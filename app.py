import os
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, jsonify

# Initialize Flask app with static file handling
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Sample data to use when the Excel file is not available
SAMPLE_COUNTER_DATA = {
    "D.Va": {
        "Role": "Tank",
        "Tank": "Zarya, Sigma",
        "Damage": "Symmetra, Sombra, Mei",
        "Support": "",
        "Weaknesses": "Weak against beam weapons that bypass Defense Matrix. Loses mech easily to focused fire."
    },
    "Genji": {
        "Role": "Damage",
        "Tank": "Winston, Zarya",
        "Damage": "Mei, Symmetra, Torbjörn",
        "Support": "Moira, Brigitte",
        "Weaknesses": "Struggles against auto-aim and beam abilities that can't be deflected. Vulnerable when Deflect is on cooldown."
    },
    "Mercy": {
        "Role": "Support",
        "Tank": "D.Va, Winston",
        "Damage": "Widowmaker, Tracer, Sombra",
        "Support": "",
        "Weaknesses": "Relies on teammates for positioning. Vulnerable while using Resurrect. Can be isolated by flankers."
    },
    "Reinhardt": {
        "Role": "Tank",
        "Tank": "Sigma, Orisa",
        "Damage": "Pharah, Echo, Junkrat",
        "Support": "",
        "Weaknesses": "Limited range. Vulnerable to aerial threats and spam damage. Shield can be broken quickly."
    },
    "Widowmaker": {
        "Role": "Damage",
        "Tank": "Winston, D.Va, Wrecking Ball",
        "Damage": "Genji, Tracer, Sombra",
        "Support": "",
        "Weaknesses": "Weak at close range. Vulnerable to dive tanks and flankers. Struggles against barriers and shields."
    }
}

def load_counter_data():
    """
    Loads data from 'Overwatch Counters.xlsx'.
    Expected columns: Role, Hero, Tank-Counter, Damage-Counter, Support-Counter, Weaknesses:
    """
    excel_file = 'Overwatch Counters.xlsx'

    try:
        if not os.path.exists(excel_file):
            print(f"Warning: Excel file '{excel_file}' not found. Using sample data.")
            return generate_sample_data()

        df = pd.read_excel(excel_file)
        df.columns = df.columns.str.strip()
        
        required_cols = ["Role", "Hero", "Tank-Counter", "Damage-Counter", "Support-Counter", "Weaknesses:"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Warning: Columns {missing_cols} not found in Excel. Using sample data.")
            return generate_sample_data()

        data = {}
        for _, row in df.iterrows():
            hero_name = str(row["Hero"]).strip()
            if hero_name.lower() == 'nan' or not hero_name:
                continue  # Skip empty entries
                
            data[hero_name] = {
                "Role": row["Role"] if not pd.isna(row["Role"]) else "Unknown",
                "Tank": str(row["Tank-Counter"]) if not pd.isna(row["Tank-Counter"]) else "",
                "Damage": str(row["Damage-Counter"]) if not pd.isna(row["Damage-Counter"]) else "",
                "Support": str(row["Support-Counter"]) if not pd.isna(row["Support-Counter"]) else "",
                "Weaknesses": str(row["Weaknesses:"]) if not pd.isna(row["Weaknesses:"]) else ""
            }

        # Group heroes by role for filtering
        roles = {
            "Tank": [],
            "Damage": [],
            "Support": [],
            "Unknown": []  # Add a category for heroes with unknown roles
        }
        
        for hero, hero_data in data.items():
            # Check if the role is valid before adding to the role list
            role = hero_data["Role"]
            if pd.isna(role) or role == "" or role not in roles:
                roles["Unknown"].append(hero)
            else:
                roles[role].append(hero)
        
        for role in roles:
            roles[role] = sorted(roles[role])
        
        # Filter out any "nan" entries that might come from empty cells
        characters = [hero for hero in sorted(data.keys()) if hero.lower() != "nan"]
        return data, characters, roles
    
    except Exception as e:
        print(f"Error loading Excel data: {e}")
        # Return sample data on error
        return generate_sample_data()

def generate_sample_data():
    """Generate sample data when the Excel file is unavailable"""
    data = SAMPLE_COUNTER_DATA
    characters = list(data.keys())
    
    roles = {
        "Tank": [],
        "Damage": [],
        "Support": [],
        "Unknown": []
    }
    
    for hero, hero_data in data.items():
        role = hero_data["Role"]
        if role in roles:
            roles[role].append(hero)
    
    for role in roles:
        roles[role] = sorted(roles[role])
    
    return data, characters, roles

# Normalization function to ensure hero names match our heroSummaries keys
def normalize_hero_name(name):
    mapping = {
        "DVa": "D.Va",
        "Ball": "Wrecking Ball",
        "Widow": "Widowmaker",
        "Soldier: 76": "Soldier: 76",
        "Soldier:76": "Soldier: 76",
        "Soldier76": "Soldier: 76",
        "Sniper/Flying": "Widowmaker",  # Best approximation for this general term
        "Brawl": "",  # This is a strategy, not a hero
        "Dive": ""    # This is a strategy, not a hero
    }
    # Return the mapped name if exists; otherwise, return the original name
    return mapping.get(name.strip(), name.strip())

# Get difficulty ratings for matchups (1-5 scale, where 5 is very effective)
def get_counter_difficulty(counter, enemy):
    # Make sure we don't compare a hero against itself
    if counter == enemy:
        return 1  # A hero is never a good counter to itself
    
    # Hero counter tiers (stored as dictionaries for faster lookup)
    effectiveness_data = {
        # Tank counters
        "D.Va": {
            "Pharah": 5, "Echo": 5, "Mercy": 4, "Widowmaker": 4, "Ashe": 4, "Hanzo": 4,
            "Bastion": 4, "Soldier: 76": 4, "Sojourn": 4, "Ana": 4, "Baptiste": 4, 
            "Cassidy": 3, "Genji": 3, "Tracer": 3, "Sombra": 2, "Zarya": 1, "Symmetra": 1,
            "Moira": 2, "Winston": 3, "Doomfist": 3, "Mei": 2, "Reaper": 2
        },
        "Zarya": {
            "D.Va": 5, "Sigma": 4, "Roadhog": 4, "Reinhardt": 4, "Winston": 4, "Wrecking Ball": 3,
            "Genji": 4, "Tracer": 4, "Sombra": 3, "Doomfist": 4, "Mei": 3, "Reaper": 3
        },
        # ... [more effectiveness data] ...
    }
    
    # Check if we have specific data for this counter against this enemy
    if counter in effectiveness_data and enemy in effectiveness_data[counter]:
        return effectiveness_data[counter][enemy]
    
    # Default to medium effectiveness if all else fails
    return 3

# Hero image URLs - updated to use local icon files with .webp extension and proper spacing handling
def get_hero_image_url(hero_name):
    # Get the hero role to use the appropriate subfolder
    role = "unknown"
    if hero_name in counterData:
        role = counterData[hero_name]["Role"].lower()
    
    # Format the hero name for the filename (maintaining the user's naming convention)
    if hero_name == "Soldier: 76":
        filename = "Icon-Soldier_76"
    else:
        # Replace spaces with underscores, and remove colons and periods
        filename = f"Icon-{hero_name.replace(' ', '_').replace(':', '').replace('.', '')}"
    
    # Full path to the hero icon using .webp extension
    return f"/static/images/heroes/{role}/{filename}.webp"

# Load the data during startup
global counterData, enemy_characters, heroes_by_role

# Try to load data from Excel first, fall back to sample data if that fails
try:
    excel_exists = os.path.exists('Overwatch Counters.xlsx')
    print(f"Excel file exists: {excel_exists}")
    
    if excel_exists:
        counterData, enemy_characters, heroes_by_role = load_counter_data()
        print(f"Loaded {len(enemy_characters)} heroes from Excel data")
    else:
        # Use sample data as fallback
        print("Excel file not found, using sample data instead")
        counterData, enemy_characters, heroes_by_role = generate_sample_data()
        print(f"Loaded {len(enemy_characters)} sample heroes")
except Exception as e:
    print(f"Error loading data: {e}")
    # Ensure we always have some data
    counterData, enemy_characters, heroes_by_role = generate_sample_data()
    print("Falling back to sample data due to error")

# ------------------------------------------------------------------
# FLASK ROUTES
# ------------------------------------------------------------------
@app.route('/')
def enemy_selection():
    print("Route: / (enemy_selection) called")
    # Create a dictionary mapping heroes to their roles
    hero_roles = {hero: counterData.get(hero, {}).get("Role", "Unknown") for hero in enemy_characters}
    
    # Return direct HTML instead of using a template
    hero_list_html = ""
    for hero in enemy_characters:
        role = hero_roles[hero]
        hero_list_html += f'<div class="hero-item">{hero} ({role})</div>'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Overwatch Counter Picker</title>
        <style>
            body {{ 
                background-color: #405275; 
                color: white; 
                font-family: Arial, sans-serif;
                padding: 20px;
            }}
            .card {{ 
                background-color: rgba(0, 0, 0, 0.6); 
                border: 2px solid #f99e1a; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px auto; 
                max-width: 800px; 
            }}
            .hero-item {{
                background-color: rgba(0, 0, 0, 0.3);
                margin: 5px;
                padding: 10px;
                border-radius: 5px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="color: #f99e1a; text-align: center;">Overwatch Counter Picker</h1>
            <p>Heroes loaded: {len(enemy_characters)}</p>
            <p>Excel file exists: {excel_exists}</p>
            <p>This is a direct HTML version of your app.</p>
            
            <h2>Available Heroes:</h2>
            <div style="display: flex; flex-wrap: wrap;">
                {hero_list_html}
            </div>
            
            <div style="margin-top: 20px;">
                <a href="/status" style="color: #f99e1a; text-decoration: none; font-weight: bold;">View App Status</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/select_class')
def select_class():
    enemy = request.args.get('enemy')
    if enemy not in counterData:
        return "Invalid enemy hero selected!", 400
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Choose Your Role - Overwatch Counter</title>
        <style>
            body {{ 
                background-color: #405275; 
                color: white; 
                font-family: Arial, sans-serif;
                padding: 20px;
            }}
            .card {{ 
                background-color: rgba(0, 0, 0, 0.6); 
                border: 2px solid #f99e1a; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px auto; 
                max-width: 800px; 
                text-align: center;
            }}
            .role-option {{
                background-color: rgba(0, 0, 0, 0.3);
                margin: 10px;
                padding: 15px;
                border-radius: 5px;
                display: inline-block;
                width: 28%;
                text-align: center;
            }}
            .role-tank {{ border-left: 4px solid #2980b9; }}
            .role-damage {{ border-left: 4px solid #c0392b; }}
            .role-support {{ border-left: 4px solid #27ae60; }}
            a {{ color: #f99e1a; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="color: #f99e1a;">Choose Your Role</h1>
            <p>Counter-picking: <strong>{enemy}</strong></p>
            
            <div style="display: flex; justify-content: center; flex-wrap: wrap;">
                <a href="/show_counters?enemy={enemy}&role=Tank" class="role-option role-tank">
                    <h2 style="color: #2980b9;">Tank</h2>
                    <p>High HP frontline heroes that create space</p>
                </a>
                
                <a href="/show_counters?enemy={enemy}&role=Damage" class="role-option role-damage">
                    <h2 style="color: #c0392b;">Damage</h2>
                    <p>High damage output heroes that secure eliminations</p>
                </a>
                
                <a href="/show_counters?enemy={enemy}&role=Support" class="role-option role-support">
                    <h2 style="color: #27ae60;">Support</h2>
                    <p>Healing heroes that keep the team alive</p>
                </a>
            </div>
            
            <div style="margin-top: 20px;">
                <a href="/" style="padding: 10px; background-color: #333; border-radius: 5px;">Back to Hero Selection</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/show_counters')
def show_counters():
    enemy = request.args.get('enemy')
    user_role = request.args.get('role')
    
    if enemy not in counterData:
        return "Invalid enemy hero!", 400
    if user_role not in ["Tank", "Damage", "Support"]:
        return "Invalid role selected!", 400

    # Get recommended counter heroes and weaknesses from the data
    counters_for_role = counterData[enemy][user_role]
    weaknesses = counterData[enemy]["Weaknesses"]

    # Parse and normalize all recommended counter heroes (assumed comma-separated)
    counters_list = [normalize_hero_name(counter.strip()) for counter in counters_for_role.split(",") if counter.strip()]
    counters_list = [c for c in counters_list if c]  # Remove empty strings (from strategy terms like "Brawl", "Dive")
    
    # Get effectiveness ratings for each counter
    effectiveness = {counter: get_counter_difficulty(counter, enemy) for counter in counters_list}
    
    # Build counters HTML
    counters_html = ""
    for counter in counters_list:
        rating = effectiveness[counter]
        counters_html += f"""
        <div style="background-color: rgba(0, 0, 0, 0.3); margin: 10px; padding: 15px; border-radius: 5px;">
            <h3>{counter}</h3>
            <p>Effectiveness: {rating}/5</p>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Counter Strategy - Overwatch Counter</title>
        <style>
            body {{ 
                background-color: #405275; 
                color: white; 
                font-family: Arial, sans-serif;
                padding: 20px;
            }}
            .card {{ 
                background-color: rgba(0, 0, 0, 0.6); 
                border: 2px solid #f99e1a; 
                border-radius: 10px; 
                padding: 20px; 
                margin: 20px auto; 
                max-width: 800px; 
            }}
            .header {{
                background: linear-gradient(135deg, #f99e1a, #218ffe);
                color: #fff;
                padding: 15px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .weakness-box {{
                background-color: rgba(231, 76, 60, 0.2);
                border-left: 4px solid #e74c3c;
                padding: 10px;
                margin-bottom: 15px;
            }}
            a {{ color: #f99e1a; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>Counter Strategy</h1>
                <span style="background-color: #333; padding: 5px 10px; border-radius: 5px;">{user_role} vs {enemy}</span>
            </div>
            
            <div style="padding: 20px;">
                <div class="weakness-box">
                    <h3>Enemy Weaknesses</h3>
                    <p>{weaknesses}</p>
                </div>
                
                <h2>Recommended Counter Heroes</h2>
                {counters_html if counters_list else "<p>No specific counters found for this role. Try another role.</p>"}
                
                <div style="margin-top: 20px; text-align: center;">
                    <a href="/select_class?enemy={enemy}" style="padding: 10px; background-color: #333; border-radius: 5px; margin-right: 10px;">Different Role</a>
                    <a href="/" style="padding: 10px; background-color: #333; border-radius: 5px;">Start Over</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/status')
def app_status():
    print("Route: /status called")
    import sys
    status_info = {
        "app_running": True,
        "excel_exists": os.path.exists('Overwatch Counters.xlsx'),
        "heroes_loaded": len(enemy_characters),
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "directory_contents": os.listdir("."),
        "template_directory_exists": os.path.exists("templates"),
        "templates_available": os.listdir("templates") if os.path.exists("templates") else []
    }
    return jsonify(status_info)

# API route to get hero data in JSON format
@app.route('/api/heroes', methods=['GET'])
def get_heroes():
    return jsonify(counterData)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app with production settings
    app.run(host='0.0.0.0', port=port)
