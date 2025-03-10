import os
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re

# Initialize Flask app with static file handling
app = Flask(__name__, 
            static_url_path='/static', 
            static_folder='static',
            template_folder=os.path.abspath('templates'))

# Configure session for storing data
app.secret_key = os.urandom(24)  # Required for session management (replace with a fixed key in production)
app.permanent_session_lifetime = timedelta(days=31)  # Session lasts 31 days

###########################################
# COMMON FUNCTIONS AND HELPERS
###########################################

# Initialize database 
def init_db():
    conn = sqlite3.connect('overwatch_app.db')
    c = conn.cursor()
    
    # Create users table for game tracker
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    ''')
    
    # Create games table for game tracker
    c.execute('''
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        map TEXT,
        hero_played TEXT,
        role TEXT,
        result TEXT,
        sr_change INTEGER,
        enemy_team TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    # Create stats table for aggregated statistics
    c.execute('''
    CREATE TABLE IF NOT EXISTS hero_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        hero TEXT,
        role TEXT,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        average_sr_change REAL DEFAULT 0.0,
        UNIQUE(user_id, hero),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('game_tracker'))
        return f(*args, **kwargs)
    return decorated_function

# Heroes and maps data for game tracker
def get_game_data():
    hero_data = {
        "Tank": [
            "D.Va", "Doomfist", "Junker Queen", "Mauga", "Orisa", "Ramattra", 
            "Reinhardt", "Roadhog", "Sigma", "Winston", "Wrecking Ball", "Zarya"
        ],
        "Damage": [
            "Ashe", "Bastion", "Cassidy", "Echo", "Genji", "Hanzo", "Junkrat", "Mei", 
            "Pharah", "Reaper", "Sojourn", "Soldier: 76", "Sombra", "Symmetra", 
            "Torbjorn", "Tracer", "Venture", "Widowmaker"
        ],
        "Support": [
            "Ana", "Baptiste", "Brigitte", "Illari", "Kiriko", "Lifeweaver", 
            "Lucio", "Mercy", "Moira", "Zenyatta"
        ]
    }
    
    maps = [
        "Ayutthaya", "Busan", "Colosseo", "Dorado", "Eichenwalde", "Esperança", 
        "Gibraltar", "Havana", "Hollywood", "Ilios", "Junkertown", "King's Row", 
        "Lijiang Tower", "Midtown", "Nepal", "New Queen Street", "Numbani", 
        "Oasis", "Paraíso", "Rialto", "Route 66", "Samoa", "Shambali", "Suravasa", 
        "Talantis", "Temple of Anubis", "Volskaya Industries"
    ]
    
    return hero_data, maps

# Load counter data from Excel for counter picker
def load_counter_data():
    """
    Loads data from 'Overwatch Counters.xlsx'.
    Expected columns: Role, Hero, Tank-Counter, Damage-Counter, Support-Counter, Weaknesses:
    """
    excel_file = 'Overwatch Counters.xlsx'

    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file '{excel_file}' not found. Please create it with the columns: Role, Hero, Tank-Counter, Damage-Counter, Support-Counter, Weaknesses:")

    df = pd.read_excel(excel_file)
    df.columns = df.columns.str.strip()
    
    required_cols = ["Role", "Hero", "Tank-Counter", "Damage-Counter", "Support-Counter", "Weaknesses:"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in Excel. Expected columns: {required_cols}")

    counterData = {}
    for _, row in df.iterrows():
        hero_name = str(row["Hero"]).strip()
        if hero_name.lower() == 'nan' or not hero_name:
            continue  # Skip empty entries
            
        counterData[hero_name] = {
            "Role": row["Role"] if not pd.isna(row["Role"]) else "Unknown",
            "Tank": str(row["Tank-Counter"]) if not pd.isna(row["Tank-Counter"]) else "",
            "Damage": str(row["Damage-Counter"]) if not pd.isna(row["Damage-Counter"]) else "",
            "Support": str(row["Support-Counter"]) if not pd.isna(row["Support-Counter"]) else "",
            "Weaknesses": str(row["Weaknesses:"]) if not pd.isna(row["Weaknesses:"]) else ""
        }

    # Group heroes by role for filtering
    heroes_by_role = {
        "Tank": [],
        "Damage": [],
        "Support": [],
        "Unknown": []  # Add a category for heroes with unknown roles
    }
    
    for hero, data in counterData.items():
        # Check if the role is valid before adding to the role list
        role = data["Role"]
        if pd.isna(role) or role == "" or role not in heroes_by_role:
            heroes_by_role["Unknown"].append(hero)
        else:
            heroes_by_role[role].append(hero)
    
    for role in heroes_by_role:
        heroes_by_role[role] = sorted(heroes_by_role[role])
    
    # Filter out any "nan" entries that might come from empty cells
    enemy_characters = [hero for hero in sorted(counterData.keys()) if hero.lower() != "nan"]
    return counterData, enemy_characters, heroes_by_role

# Normalization function to ensure hero names match our heroSummaries keys
def normalize_hero_name(name):
    mapping = {
        "DVa": "D.Va",
        "Ball": "Wrecking Ball",
        "Widow": "Widowmaker",
        "Soldier: 76": "Soldier: 76",
        "Soldier:76": "Soldier: 76",
        "Soldier76": "Soldier: 76",
        "Torb": "Torbjorn",
        "Lucio": "Lucio",
        "Sniper/Flying": "Widowmaker",  # Best approximation for this general term
        "Brawl": "",  # This is a strategy, not a hero
        "Dive": ""    # This is a strategy, not a hero
    }
    # Return the mapped name if exists; otherwise, return the original name
    return mapping.get(name.strip(), name.strip())

# Get hero role
def get_hero_role(hero, hero_data):
    for role, heroes in hero_data.items():
        if hero in heroes:
            return role
    return "Unknown"

# Generate a hero image path - works for both counter picker and game tracker
def get_hero_image_url(hero_name):
    """Generate a hero image path - works for both counter picker and game tracker"""
    # Format the hero name for the filename
    if hero_name == "Soldier: 76":
        filename = "Soldier_76"
    elif hero_name == "D.Va":
        filename = "DVa"
    else:
        # Replace spaces with underscores, remove periods
        filename = hero_name.replace(' ', '_').replace('.', '')
    
    # Add the "Icon-" prefix
    filename = f"Icon-{filename}"
    
    # Get hero role to use in path
    hero_data, _ = get_game_data()
    role = "unknown"
    
    for r, heroes in hero_data.items():
        if hero_name in heroes:
            role = r.lower()
            break
            
    # Return the URL path
    return f"/static/images/heroes/{role}/{filename}.webp"

# Get difficulty ratings for matchups (1-5 scale, where 5 is very effective)
def get_counter_difficulty(counter, enemy, counterData=None):
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
        "Winston": {
            "Widowmaker": 5, "Hanzo": 4, "Ana": 4, "Zenyatta": 5, "Ashe": 4, "Genji": 4,
            "Mercy": 4, "Venture": 5, "Illari": 4
        },
        "Wrecking Ball": {
            "Widowmaker": 4, "Hanzo": 3, "Ana": 4, "Zenyatta": 5, "Venture": 3, "Illari": 4
        },
        "Sigma": {
            "Junkrat": 4, "Hanzo": 3, "Bastion": 3, "Pharah": 3, "Echo": 3
        },
        
        # Damage counters
        "Widowmaker": {
            "Pharah": 5, "Echo": 5, "Mercy": 4, "Zenyatta": 5, "Ana": 4, "Baptiste": 4,
            "Ashe": 4, "Illari": 3, "Venture": 3
        },
        "Sombra": {
            "Zenyatta": 5, "Doomfist": 5, "Wrecking Ball": 5, "Illari": 5, "Venture": 4
        },
        "Genji": {
            "Zenyatta": 5, "Ana": 4, "Widowmaker": 4, "Ashe": 4, "Illari": 4, "Venture": 3
        },
        "Tracer": {
            "Zenyatta": 5, "Ana": 4, "Widowmaker": 4, "Ashe": 3, "Illari": 4, "Venture": 3
        },
        "Reaper": {
            "Winston": 5, "Roadhog": 4, "D.Va": 4, "Reinhardt": 4, "Venture": 3
        },
        "Pharah": {
            "Junkrat": 5, "Reinhardt": 4, "Symmetra": 4, "Mei": 4, "Reaper": 4,
            "Venture": 2
        },
        "Echo": {
            "Bastion": 4, "Reinhardt": 4, "Symmetra": 4, "Mei": 3, "Torbjörn": 4,
            "Venture": 2
        },
        "Venture": {
            "Pharah": 4, "Echo": 4, "Mercy": 3, "Widowmaker": 4, "Ashe": 3, "Tracer": 3,
            "Genji": 3, "Soldier: 76": 3, "Hanzo": 3, "Bastion": 2, "Sombra": 2, "Reaper": 2
        },
        
        # Support counters
        "Ana": {
            "Roadhog": 5, "Wrecking Ball": 4, "Winston": 3, "Venture": 3
        },
        "Zenyatta": {
            "Roadhog": 4, "Reinhardt": 3, "Zarya": 3, "Venture": 3
        },
        "Illari": {
            "Pharah": 4, "Echo": 4, "Mercy": 3, "Winston": 3, "Wrecking Ball": 3, 
            "Roadhog": 3, "Reaper": 3, "Junkrat": 3, "Genji": 2, "Tracer": 2, "Sombra": 1,
            "Venture": 3
        }
    }
    
    # Check if we have specific data for this counter against this enemy
    if counter in effectiveness_data and enemy in effectiveness_data[counter]:
        return effectiveness_data[counter][enemy]
    
    # If no specific rating exists, use role-based effectiveness
    # Check if we have counter data to get roles
    if counterData:
        # Get the roles of both heroes if available
        counter_role = counterData.get(counter, {}).get("Role", "Unknown")
        enemy_role = counterData.get(enemy, {}).get("Role", "Unknown")
        
        # These coefficients represent how effective each role is against others in general
        role_effectiveness = {
            "Tank": {"Tank": 3, "Damage": 2, "Support": 3},
            "Damage": {"Tank": 3, "Damage": 3, "Support": 4},
            "Support": {"Tank": 2, "Damage": 2, "Support": 3}
        }
        
        # If we have both roles, use the role effectiveness matrix
        if counter_role in role_effectiveness and enemy_role in role_effectiveness[counter_role]:
            return role_effectiveness[counter_role][enemy_role]
    
    # Default to medium effectiveness if all else fails
    return 3

# Hero summaries for tips
def get_hero_summaries():
    return {
        "D.Va": "Use Defense Matrix for critical projectiles and ultimates. Dive with Boosters and follow up with Micro Missiles for burst damage.",
        "Doomfist": "Engage with melee combos and use Power Block to absorb damage. Time your Charge to secure kills.",
        "Junker Queen": "Pull enemies in with your blade and follow up with Carnage. Use Commanding Shout to boost your team.",
        "Mauga": "Exploit your aggressive kit to pressure foes; use mobility to dodge key attacks, but mind long-range poke.",
        "Orisa": "Leverage your Barrier Shield and Energy Javelin to control space. Use Javelin Spin to close gaps.",
        "Ramattra": "Switch between ranged staff and melee Nemesis form to adapt. Use Ravenous Vortex to slow and pull enemies.",
        "Reinhardt": "Use your Barrier Shield to protect allies and close in with Fire Strike and Charge. Time Earthshatter to stun multiple foes.",
        "Roadhog": "Hook isolated targets and follow up with your Scrap Gun for instant kills. Use Take a Breather wisely.",
        "Sigma": "Deploy your Experimental Barrier and Kinetic Grasp to absorb damage. Use Accretion to stun and Hyperspheres for steady DPS.",
        "Winston": "Leap into enemy lines with Jump Pack and use Tesla Cannon for multi-target damage. Barrier Projector helps protect your team.",
        "Wrecking Ball": "Grapple to build momentum and disrupt enemy formations. Use adaptive shields and Piledriver for burst damage.",
        "Zarya": "Charge energy with Particle Barriers and Projected Barriers, then unleash a powerful beam. Timing your barriers is key.",
        "Ashe": "Aim for headshots with your Viper rifle and use Dynamite to burst clusters. Coach Gun offers mobility.",
        "Bastion": "Toggle between turret mode for massive DPS and mobile mode to reposition. Use your grenade to finish off targets.",
        "Cassidy": "Land precise headshots with your Peacekeeper and combo with Magnetic Grenade for burst damage. Roll to reload and reposition.",
        "Echo": "Combo Sticky Bombs with Focusing Beam for high burst; use flight to outmaneuver opponents. Duplicate smartly to adapt.",
        "Genji": "Utilize shurikens and Swift Strike for burst combos, and deflect enemy fire to turn damage back at them.",
        "Hanzo": "Aim for headshots with Storm Bow and use Sonic Arrow to reveal enemy positions. Dragonstrike zones and forces enemies out of cover.",
        "Junkrat": "Spam grenades for area denial and use Concussion Mine for burst damage and repositioning. Mine jumps add unexpected mobility.",
        "Mei": "Slow enemies with your Endothermic Blaster and block advances with Ice Wall. Cryo-Freeze lets you reset health in critical moments.",
        "Pharah": "Stay airborne to rain down rockets and use Concussive Blast to reposition. Focus on aerial pickoffs while staying out of hitscan range.",
        "Reaper": "Close in for heavy shotgun burst and lifesteal, but use Wraith Form to escape danger. Flank key targets for high-value picks.",
        "Sojourn": "Charge your railgun for lethal bursts and use Power Slide for agile repositioning. Disrupt enemies with Disruptor Shot.",
        "Soldier: 76": "Leverage your Heavy Pulse Rifle for consistent hitscan damage and use Helix Rockets for burst. Deploy Biotic Field to sustain.",
        "Sombra": "Hack priority targets to disable abilities and use stealth for backline infiltration. Translocate quickly to escape or reposition.",
        "Symmetra": "Charge your beam for high DPS in close quarters and deploy turrets to control space. Use Teleporter for rapid repositioning.",
        "Torbjörn": "Deploy your turret strategically and use Overload for increased damage. Molten Core zones enemy advances effectively.",
        "Tracer": "Exploit rapid blinks and Recall to pick off isolated squishies. Use Pulse Bomb for high burst and stay unpredictable.",
        "Venture": "Use grappling and climbing to maintain high ground advantage. Deploy Stalker Mines tactically and charge the rail gun for precision shots.",
        "Widowmaker": "Set up on high ground to land critical headshots and use Grappling Hook to reposition quickly. Venom Mine deters enemy flankers.",
        "Ana": "Use Biotic Grenade to disable enemy healing and Sleep Dart to neutralize high-priority targets. Aim for headshots to maximize burst.",
        "Baptiste": "Utilize Immortality Field to protect your team and Amplification Matrix to boost damage output. Position well for sustained fights.",
        "Brigitte": "Use Shield Bash and Whip Shot to stun enemies while inspiring allies with healing. Peel off divers to keep your team safe.",
        "Illari": "Position Solar Shrine in protected locations with good team coverage. Balance DPS and healing based on team needs.",
        "Kiriko": "Teleport swiftly and cleanse harmful effects with Suzu. Use precise aim and mobility to support your team in high-pressure moments.",
        "Lifeweaver": "Focus on efficient healing and smart crowd control. Position centrally to maximize your supportive impact.",
        "Lúcio": "Switch between speed boost and healing aura to control the pace of battle. Use sound barriers to block enemy ultimates.",
        "Mercy": "Deliver high single-target healing and damage boosts. Use Guardian Angel to reposition swiftly and keep your team in the fight.",
        "Moira": "Blend healing with damage by using Biotic Orbs effectively, and use Fade to dodge CC. Balance your dual role to sustain and pressure enemies.",
        "Zenyatta": "Apply Orb of Discord to amplify damage on targets and dish consistent DPS with Orb of Destruction. Provide clutch Transcendence when needed."
    }

# Hero difficulty data
def get_hero_difficulty():
    return {
        # Tanks
        "D.Va": 2,
        "Doomfist": 3,
        "Junker Queen": 2,
        "Mauga": 1,
        "Orisa": 1,
        "Ramattra": 2,
        "Reinhardt": 1,
        "Roadhog": 1,
        "Sigma": 2,
        "Winston": 2,
        "Wrecking Ball": 3,
        "Zarya": 2,
        
        # Damage
        "Ashe": 2,
        "Bastion": 1,
        "Cassidy": 2,
        "Echo": 3,
        "Genji": 3,
        "Hanzo": 3,
        "Junkrat": 1,
        "Mei": 2,
        "Pharah": 2,
        "Reaper": 1,
        "Sojourn": 2,
        "Soldier: 76": 1,
        "Sombra": 3,
        "Symmetra": 1,
        "Torbjörn": 1,
        "Tracer": 3,
        "Venture": 3,
        "Widowmaker": 3,
        
        # Support
        "Ana": 3,
        "Baptiste": 2,
        "Brigitte": 1,
        "Illari": 2,
        "Kiriko": 3,
        "Lifeweaver": 3,
        "Lúcio": 2,
        "Mercy": 1,
        "Moira": 1,
        "Zenyatta": 2
    }

###########################################
# ROUTES FOR BOTH APPLICATIONS
###########################################

# Home page - serves as a landing for both apps
@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html',
                         logged_in=session.get('logged_in', False),
                         user_id=session.get('user_id', None))

# Authentication and user management routes
@app.route('/set_user_id', methods=['POST'])
def set_user_id():
    """Register a new user or login an existing user"""
    user_id = request.form.get('user_id')
    password = request.form.get('password')
    
    if not user_id or not password:
        flash('User ID and password are required', 'error')
        return redirect(url_for('game_tracker'))
    
    conn = sqlite3.connect('overwatch_app.db')
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT password_hash FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    
    if request.form.get('action') == 'register':
        if user:
            conn.close()
            flash('User ID already exists', 'error')
            return redirect(url_for('game_tracker'))
            
        # Hash the password and create new user
        password_hash = generate_password_hash(password)
        c.execute('INSERT INTO users (user_id, password_hash) VALUES (?, ?)',
                 (user_id, password_hash))
        conn.commit()
        flash('Registration successful!', 'success')
        
    else:  # Login
        if not user or not check_password_hash(user[0], password):
            conn.close()
            flash('Invalid user ID or password', 'error')
            return redirect(url_for('game_tracker'))
            
        # Update last login time
        c.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?',
                 (user_id,))
        conn.commit()
        flash('Login successful!', 'success')
    
    conn.close()
    
    # Set up session
    session.permanent = True
    session['user_id'] = user_id
    session['logged_in'] = True
    
    return redirect(url_for('game_tracker'))

@app.route('/logout')
def logout():
    """Log out the current user"""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('game_tracker'))

###########################################
# COUNTER PICKER ROUTES
###########################################

@app.route('/counter')
def enemy_selection():
    """Counter picker homepage"""
    try:
        # Load counter data
        counterData, enemy_characters, heroes_by_role = load_counter_data()
        hero_roles = {hero: counterData[hero]["Role"] for hero in enemy_characters}
        
        return render_template('counter_index.html',
            enemies=enemy_characters, 
            hero_roles=hero_roles,
            hero_image_url=get_hero_image_url,
            logged_in=session.get('logged_in', False),
            user_id=session.get('user_id', None)
        )
    except Exception as e:
        flash(f'Error loading counter data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/multi_enemy')
def multi_enemy_selection():
    """Multi-enemy counter picker page"""
    try:
        # Load counter data
        counterData, enemy_characters, heroes_by_role = load_counter_data()
        hero_roles = {hero: counterData[hero]["Role"] for hero in enemy_characters}
        
        return render_template('multi_enemy.html', 
            enemies=enemy_characters, 
            hero_roles=hero_roles,
            hero_image_url=get_hero_image_url,
            logged_in=session.get('logged_in', False),
            user_id=session.get('user_id', None)
        )
    except Exception as e:
        flash(f'Error loading counter data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/select_class')
def select_class():
    """Class selection for counter picking"""
    enemy = request.args.get('enemy')
    
    try:
        counterData, _, _ = load_counter_data()
        
        if enemy not in counterData:
            flash('Invalid enemy hero selected!', 'error')
            return redirect(url_for('enemy_selection'))
            
        return render_template('select_role.html', 
                              enemy=enemy,
                              logged_in=session.get('logged_in', False),
                              user_id=session.get('user_id', None))
    except Exception as e:
        flash(f'Error loading hero data: {str(e)}', 'error')
        return redirect(url_for('enemy_selection'))

@app.route('/select_class_multi')
def select_class_multi():
    """Class selection for multi-enemy counter picking"""
    enemies = request.args.get('enemies', '').split(',')
    if not enemies or enemies[0] == '':
        return redirect(url_for('multi_enemy_selection'))
    
    # Store enemies in session for later use
    session['selected_enemies'] = enemies
    
    return render_template('select_role_multi.html', 
                          enemies=enemies, 
                          hero_image_url=get_hero_image_url,
                          logged_in=session.get('logged_in', False),
                          user_id=session.get('user_id', None))

@app.route('/show_counters')
def show_counters():
    """Show counter recommendations for single enemy"""
    enemy = request.args.get('enemy')
    role = request.args.get('role')
    
    if not enemy or not role:
        flash("Missing parameters!", 'error')
        return redirect(url_for('enemy_selection'))
    
    try:
        counterData, _, _ = load_counter_data()
        
        if enemy not in counterData:
            flash("Invalid enemy hero!", 'error')
            return redirect(url_for('enemy_selection'))
            
        if role not in ["Tank", "Damage", "Support"]:
            flash("Invalid role selected!", 'error')
            return redirect(url_for('select_class', enemy=enemy))

        # Get recommended counter heroes and weaknesses from the data
        counters_for_role = counterData[enemy][role]
        weaknesses = counterData[enemy]["Weaknesses"]

        # Parse and normalize all recommended counter heroes
        counters_list = [normalize_hero_name(counter.strip()) for counter in counters_for_role.split(",") if counter.strip()]
        counters_list = [c for c in counters_list if c]  # Remove empty strings
        
        # Get effectiveness ratings for each counter
        effectiveness = {counter: get_counter_difficulty(counter, enemy, counterData) for counter in counters_list}
        
        # Get hero tips
        hero_summaries = get_hero_summaries()
        hero_tips = {counter: hero_summaries.get(counter, f"Use {counter}'s abilities to counter {enemy}'s strengths.") for counter in counters_list}
        
        # Get hero difficulty ratings
        hero_difficulty = get_hero_difficulty()
        difficulties = {counter: hero_difficulty.get(counter, 2) for counter in counters_list}  # Default to medium if not found
        difficulty_text = {counter: ["Easy", "Medium", "Hard"][difficulties[counter]-1] for counter in counters_list}
        
        # Find beginner-friendly recommendations (easy heroes with high effectiveness)
        beginner_friendly = [counter for counter in counters_list 
                            if difficulties.get(counter, 2) == 1 and effectiveness.get(counter, 0) >= 4]

        return render_template('counters.html',
            enemy=enemy,
            user_role=role,
            counters_list=counters_list,
            weaknesses=weaknesses,
            effectiveness=effectiveness,
            hero_tips=hero_tips,
            difficulties=difficulties,
            difficulty_text=difficulty_text,
            beginner_friendly=beginner_friendly,
            hero_difficulty=hero_difficulty,
            difficulty_labels={1: "Easy", 2: "Medium", 3: "Hard"},
            hero_image_url=get_hero_image_url,
            logged_in=session.get('logged_in', False),
            user_id=session.get('user_id', None)
        )
        
    except Exception as e:
        flash(f'Error loading counter data: {str(e)}', 'error')
        return redirect(url_for('enemy_selection'))

@app.route('/show_multi_counters')
def show_multi_counters():
    """Show counter recommendations for multiple enemies"""
    enemies = session.get('selected_enemies', [])
    role = request.args.get('role')
    
    if not enemies or role not in ["Tank", "Damage", "Support"]:
        flash("Invalid selection. Please try again.", 'error')
        return redirect(url_for('multi_enemy_selection'))

    try:
        counterData, _, heroes_by_role = load_counter_data()
        
        # Get all heroes in the selected role
        role_heroes = heroes_by_role[role]
        
        # Calculate effectiveness against the enemy team
        counter_scores = {}
        individual_scores = {}
        
        for hero in role_heroes:
            counter_scores[hero] = 0
            individual_scores[hero] = {}
            
            for enemy in enemies:
                if enemy in counterData:  # Make sure the enemy exists in our data
                    score = get_counter_difficulty(hero, enemy, counterData)
                    counter_scores[hero] += score
                    individual_scores[hero][enemy] = score
                
            # Average the score
            if len(enemies) > 0:
                counter_scores[hero] /= len(enemies)
        
        # Sort by effectiveness
        sorted_counters = sorted(counter_scores.items(), key=lambda x: x[1], reverse=True)
        top_counters = [hero for hero, score in sorted_counters[:5]]  # Top 5 counters
        
        # Get weaknesses for all enemies
        all_weaknesses = {enemy: counterData.get(enemy, {}).get("Weaknesses", "") for enemy in enemies}
        
        # Get hero tips
        hero_summaries = get_hero_summaries()
        hero_tips = {counter: hero_summaries.get(counter, f"Use {counter}'s abilities to counter multiple enemies.") for counter in top_counters}
        
        # Get hero difficulty ratings
        hero_difficulty = get_hero_difficulty()
        difficulties = {counter: hero_difficulty.get(counter, 2) for counter in top_counters}
        difficulty_text = {counter: ["Easy", "Medium", "Hard"][difficulties[counter]-1] for counter in top_counters}
        
        # Find beginner-friendly recommendations (easy heroes with good effectiveness)
        beginner_friendly = [counter for counter in top_counters 
                            if difficulties.get(counter, 2) == 1 and counter_scores.get(counter, 0) >= 3.5]

        return render_template('multi_counters.html',
            enemies=enemies,
            user_role=role,
            counters_list=top_counters,
            effectiveness=dict(sorted_counters),
            individual_scores=individual_scores,
            hero_tips=hero_tips,
            difficulties=difficulties,
            difficulty_text=difficulty_text,
            beginner_friendly=beginner_friendly,
            all_weaknesses=all_weaknesses,
            hero_difficulty=hero_difficulty,
            difficulty_labels={1: "Easy", 2: "Medium", 3: "Hard"},
            hero_image_url=get_hero_image_url,
            logged_in=session.get('logged_in', False),
            user_id=session.get('user_id', None)
        )
    except Exception as e:
        flash(f'Error loading counter data: {str(e)}', 'error')
        return redirect(url_for('multi_enemy_selection'))

###########################################
# GAME TRACKER ROUTES 
###########################################

@app.route('/tracker')
def game_tracker():
    """Main game tracker page"""
    # Get user_id from session
    user_id = session.get('user_id', None)
    logged_in = session.get('logged_in', False)
    
    # Get hero and map data
    hero_data, maps = get_game_data()
    all_heroes = []
    for role_heroes in hero_data.values():
        all_heroes.extend(role_heroes)
    all_heroes.sort()
    
    recent_games = []
    hero_stats = []
    
    if user_id and logged_in:
        # Get recent games for this user
        conn = sqlite3.connect('overwatch_app.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('''
        SELECT * FROM games 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        LIMIT 10
        ''', (user_id,))
        recent_games = c.fetchall()
        
        # Get hero statistics
        c.execute('''
        SELECT * FROM hero_stats
        WHERE user_id = ?
        ORDER BY games_played DESC
        ''', (user_id,))
        hero_stats = c.fetchall()
        
        conn.close()
    
    return render_template('game_tracker.html',
        recent_games=recent_games,
        hero_stats=hero_stats,
        all_heroes=all_heroes,
        hero_data=hero_data,
        maps=maps,
        roles=["Tank", "Damage", "Support"],
        get_hero_image_url=get_hero_image_url,
        user_id=user_id,
        logged_in=logged_in
    )

@app.route('/add_game', methods=['POST'])
@login_required
def add_game():
    """Add a new game to the tracker"""
    user_id = session['user_id']
    
    # Get form data
    map_name = request.form.get('map', '')
    hero_played = request.form.get('hero', '')
    role = request.form.get('role', '')
    result = request.form.get('result', '')
    sr_change = request.form.get('sr_change', 0)
    
    # Validate sr_change is an integer
    try:
        sr_change = int(sr_change)
    except ValueError:
        sr_change = 0
    
    enemy_team = request.form.get('enemy_team', '')
    notes = request.form.get('notes', '')
    
    # Connect to database
    conn = sqlite3.connect('overwatch_app.db')
    c = conn.cursor()
    
    # Insert game record
    c.execute('''
    INSERT INTO games (user_id, map, hero_played, role, result, sr_change, enemy_team, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, map_name, hero_played, role, result, sr_change, enemy_team, notes))
    
    # Update stats for this hero
    c.execute('''
    INSERT INTO hero_stats (user_id, hero, role, games_played, wins, losses, draws, average_sr_change)
    VALUES (?, ?, ?, 1, ?, ?, ?, ?)
    ON CONFLICT(user_id, hero) DO UPDATE SET
        games_played = games_played + 1,
        wins = wins + CASE WHEN ? = 'win' THEN 1 ELSE 0 END,
        losses = losses + CASE WHEN ? = 'loss' THEN 1 ELSE 0 END,
        draws = draws + CASE WHEN ? = 'draw' THEN 1 ELSE 0 END,
        average_sr_change = (average_sr_change * games_played + ?) / (games_played + 1)
    ''', (
        user_id, 
        hero_played,
        role, 
        1 if result == 'win' else 0,
        1 if result == 'loss' else 0,
        1 if result == 'draw' else 0,
        sr_change,
        result, result, result,
        sr_change
    ))
    
    conn.commit()
    conn.close()
    
    flash('Game added successfully!', 'success')
    return redirect(url_for('game_tracker'))

@app.route('/delete_game/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    """Delete a game record"""
    user_id = session['user_id']
    
    conn = sqlite3.connect('overwatch_app.db')
    c = conn.cursor()
    
    # Get game details before deletion to update stats
    c.execute('SELECT hero_played, role, result, sr_change FROM games WHERE id = ? AND user_id = ?', 
             (game_id, user_id))
    game = c.fetchone()
    
    if game:
        hero_played, role, result, sr_change = game
        
        # Delete the game
        c.execute('DELETE FROM games WHERE id = ? AND user_id = ?', (game_id, user_id))
        
        # Update hero stats
        if result == 'win':
            win_adj, loss_adj, draw_adj = -1, 0, 0
        elif result == 'loss':
            win_adj, loss_adj, draw_adj = 0, -1, 0
        elif result == 'draw':
            win_adj, loss_adj, draw_adj = 0, 0, -1
        else:
            win_adj, loss_adj, draw_adj = 0, 0, 0
        
        c.execute('''
        UPDATE hero_stats 
        SET games_played = games_played - 1,
            wins = wins + ?,
            losses = losses + ?,
            draws = draws + ?
        WHERE user_id = ? AND hero = ? AND games_played > 0
        ''', (win_adj, loss_adj, draw_adj, user_id, hero_played))
        
        # If hero has no games left, remove the record
        c.execute('''
        DELETE FROM hero_stats
        WHERE user_id = ? AND hero = ? AND games_played <= 0
        ''', (user_id, hero_played))
        
        conn.commit()
        flash('Game deleted successfully!', 'success')
    else:
        flash('Game not found!', 'error')
    
    conn.close()
    return redirect(url_for('game_tracker'))

@app.route('/hero_stats/<hero>')
@login_required
def hero_stats(hero):
    """Detailed view of a specific hero's performance"""
    user_id = session['user_id']
    
    conn = sqlite3.connect('overwatch_app.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get hero stats
    c.execute('''
    SELECT * FROM hero_stats
    WHERE user_id = ? AND hero = ?
    ''', (user_id, hero))
    stats = c.fetchone()
    
    # Get all games with this hero
    c.execute('''
    SELECT * FROM games
    WHERE user_id = ? AND hero_played = ?
    ORDER BY created_at DESC
    ''', (user_id, hero))
    games = c.fetchall()
    
    # Get map performance
    c.execute('''
    SELECT map, 
           COUNT(*) as games_played,
           SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses
    FROM games
    WHERE user_id = ? AND hero_played = ?
    GROUP BY map
    ORDER BY wins DESC
    ''', (user_id, hero))
    map_stats = c.fetchall()
    
    conn.close()
    
    # Get hero role for UI styling
    hero_data, _ = get_game_data()
    hero_role = get_hero_role(hero, hero_data)
    
    return render_template('hero_stats.html',
        hero=hero,
        hero_role=hero_role,
        stats=stats,
        games=games,
        map_stats=map_stats,
        get_hero_image_url=get_hero_image_url,
        logged_in=session.get('logged_in', False),
        user_id=session.get('user_id', None)
    )

@app.route('/overall_stats')
@login_required
def overall_stats():
    """Overall statistics view"""
    user_id = session['user_id']
    
    conn = sqlite3.connect('overwatch_app.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get overall stats
    c.execute('''
    SELECT 
        COUNT(*) as total_games,
        SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as total_wins,
        SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as total_losses,
        SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) as total_draws,
        AVG(sr_change) as avg_sr_change
    FROM games
    WHERE user_id = ?
    ''', (user_id,))
    overall = c.fetchone()
    
    # Get role stats
    c.execute('''
    SELECT 
        role,
        COUNT(*) as games_played,
        SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) as draws
    FROM games
    WHERE user_id = ?
    GROUP BY role
    ''', (user_id,))
    role_stats = c.fetchall()
    
    # Get best heroes by win rate (min 3 games)
    c.execute('''
    SELECT 
        hero,
        role,
        games_played,
        wins,
        CAST(wins as FLOAT) / games_played as win_rate,
        average_sr_change
    FROM hero_stats
    WHERE user_id = ? AND games_played >= 3
    ORDER BY win_rate DESC
    LIMIT 5
    ''', (user_id,))
    best_heroes = c.fetchall()
    
    # Get recent SR trend
    c.execute('''
    SELECT created_at, sr_change, result
    FROM games
    WHERE user_id = ?
    ORDER BY created_at ASC
    LIMIT 20
    ''', (user_id,))
    sr_trend = c.fetchall()
    
    conn.close()
    
    return render_template('overall_stats.html',
        overall=overall,
        role_stats=role_stats,
        best_heroes=best_heroes,
        sr_trend=sr_trend,
        get_hero_image_url=get_hero_image_url,
        logged_in=session.get('logged_in', False),
        user_id=session.get('user_id', None)
    )

# Initialize database when app starts
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=False)