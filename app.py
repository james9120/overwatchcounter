import os
import pandas as pd
from flask import Flask, request, render_template_string, redirect, url_for, jsonify

# Initialize Flask app with static file handling
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Global variables for data
counterData = {}
enemy_characters = []
heroes_by_role = {"Tank": [], "Damage": [], "Support": [], "Unknown": []}

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
    
    # If no specific rating exists, we'll use role-based effectiveness
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
        base_effectiveness = role_effectiveness[counter_role][enemy_role]
        
        # Further adjust based on hero archetypes
        # Tanks
        if counter in ["Roadhog", "Zarya", "D.Va"] and enemy_role == "Damage":
            base_effectiveness += 1
        elif counter in ["Winston", "D.Va", "Wrecking Ball"] and enemy in ["Widowmaker", "Ashe", "Hanzo", "Venture"]:
            base_effectiveness += 1
        elif counter in ["Reinhardt", "Orisa", "Sigma"] and enemy in ["Junkrat", "Pharah", "Echo"]:
            base_effectiveness -= 1
            
        # Damage
        if counter in ["Widowmaker", "Ashe", "Soldier: 76", "Sojourn", "Venture"] and enemy in ["Pharah", "Echo", "Mercy"]:
            base_effectiveness += 1
        elif counter in ["Reaper", "Mei", "Symmetra"] and enemy_role == "Tank":
            base_effectiveness += 1
        elif counter in ["Genji", "Tracer", "Sombra"] and enemy_role == "Support":
            base_effectiveness += 1
            
        # Support
        if counter in ["Ana", "Illari"] and enemy in ["Roadhog", "Winston", "Wrecking Ball"]:
            base_effectiveness += 1
        elif counter in ["Brigitte", "Moira"] and enemy in ["Genji", "Tracer"]:
            base_effectiveness += 1
            
        # Ensure we stay within 1-5 range
        return max(1, min(5, base_effectiveness))
    
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

# Hero difficulty ratings (1-3 scale)
# 1 = Easy: Simple mechanics, forgiving gameplay, good for beginners
# 2 = Medium: Requires some game knowledge and mechanical skill
# 3 = Hard: Complex mechanics, high skill ceiling, requires significant practice
hero_difficulty = {
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
    "Lucio": 2,
    "Mercy": 1,
    "Moira": 1,
    "Zenyatta": 2
}

# Descriptive labels for difficulty levels
difficulty_labels = {
    1: "Easy",
    2: "Medium",
    3: "Hard"
}

# ------------------------------------------------------------------
# HERO SUMMARIES: Tactical tips for each recommended counter hero.
# All keys now use consistent naming.
# ------------------------------------------------------------------
heroSummaries = {
    "D.Va": "Use Defense Matrix for critical projectiles and ultimates. Dive with Boosters and follow up with Micro Missiles for burst damage. Time Self-Destruct for area denial, and watch out for beam heroes.",
    "Doomfist": "Engage with melee combos and use Power Block to absorb damage. Time your Charge to secure kills, but avoid heavy crowd-control.",
    "Junker Queen": "Pull enemies in with your blade and follow up with Carnage. Use Commanding Shout to boost your team and sustain in close brawls.",
    "Mauga": "Exploit your aggressive kit to pressure foes; use mobility to dodge key attacks, but mind long-range poke.",
    "Orisa": "Leverage your Barrier Shield and Energy Javelin to control space. Use Javelin Spin to close gaps and disrupt enemy formations.",
    "Ramattra": "Switch between ranged staff and melee Nemesis form to adapt. Use Ravenous Vortex to slow and pull enemies into your burst.",
    "Reinhardt": "Use your Barrier Shield to protect allies and close in with Fire Strike and Charge. Time Earthshatter to stun multiple foes.",
    "Roadhog": "Hook isolated targets and follow up with your Scrap Gun for instant kills. Use Take a Breather wisely to sustain without overextending.",
    "Sigma": "Deploy your Experimental Barrier and Kinetic Grasp to absorb damage. Use Accretion to stun and Hyperspheres for steady DPS.",
    "Winston": "Leap into enemy lines with Jump Pack and use Tesla Cannon for multi-target damage. Barrier Projector helps protect your team during dives.",
    "Wrecking Ball": "Grapple to build momentum and disrupt enemy formations. Use adaptive shields and Piledriver for burst damage.",
    "Zarya": "Charge energy with Particle Barriers and Projected Barriers, then unleash a powerful beam. Timing your barriers is key to survival.",
    "Ashe": "Aim for headshots with your Viper rifle and use Dynamite to burst clusters. Coach Gun offers mobility—use it to reposition after a pick.",
    "Bastion": "Toggle between turret mode for massive DPS and mobile mode to reposition. Use your grenade to finish off low-health targets.",
    "Cassidy": "Land precise headshots with your Peacekeeper and combo with Magnetic Grenade for burst damage. Roll to reload and reposition swiftly.",
    "Echo": "Combo Sticky Bombs with Focusing Beam for high burst; use flight to outmaneuver opponents. Duplicate smartly to adapt to fights.",
    "Genji": "Utilize shurikens and Swift Strike for burst combos, and deflect enemy fire to turn damage back at them. Dragonblade can wipe foes if timed well.",
    "Hanzo": "Aim for headshots with Storm Bow and use Sonic Arrow to reveal enemy positions. Dragonstrike zones and forces enemies out of cover.",
    "Junkrat": "Spam grenades for area denial and use Concussion Mine for burst damage and repositioning. Mine jumps add unexpected mobility.",
    "Mei": "Slow enemies with your Endothermic Blaster and block advances with Ice Wall. Cryo-Freeze lets you reset health in critical moments.",
    "Pharah": "Stay airborne to rain down rockets and use Concussive Blast to reposition. Focus on aerial pickoffs while staying out of hitscan range.",
    "Reaper": "Close in for heavy shotgun burst and lifesteal, but use Wraith Form to escape danger. Flank key targets for high-value picks.",
    "Sojourn": "Charge your railgun for lethal bursts and use Power Slide for agile repositioning. Disrupt enemies with Disruptor Shot and Overclock for multi-kills.",
    "Soldier: 76": "Leverage your Heavy Pulse Rifle for consistent hitscan damage and use Helix Rockets for burst. Deploy Biotic Field to sustain yourself and your team, and use Sprint to reposition quickly.",
    "Sombra": "Hack priority targets to disable abilities and use stealth for backline infiltration. Translocate quickly to escape or reposition.",
    "Symmetra": "Charge your beam for high DPS in close quarters and deploy turrets to control space. Use Teleporter for rapid repositioning.",
    "Torbjörn": "Deploy your turret strategically and use Overload for increased damage. Molten Core zones enemy advances effectively.",
    "Tracer": "Exploit rapid blinks and Recall to pick off isolated squishies. Use Pulse Bomb for high burst and stay unpredictable.",
    "Venture": "Use grappling and climbing to maintain high ground advantage. Deploy Stalker Mines tactically and charge the rail gun for high damage precision shots.",
    "Widowmaker": "Set up on high ground to land critical headshots and use Grappling Hook to reposition quickly. Venom Mine deters enemy flankers.",
    "Ana": "Use Biotic Grenade to disable enemy healing and Sleep Dart to neutralize high-priority targets. Aim for headshots to maximize burst.",
    "Baptiste": "Utilize Immortality Field to protect your team and Amplification Matrix to boost damage output. Position well for sustained fights.",
    "Brigitte": "Use Shield Bash and Whip Shot to stun enemies while inspiring allies with healing. Peel off divers to keep your team safe.",
    "Illari": "Position Solar Shrine in protected locations with good team coverage. Balance DPS and healing based on team needs. Use high ground to maximize projectile effectiveness. Save Captive Sun for finishing low-health targets or area denial.",
    "Kiriko": "Teleport swiftly and cleanse harmful effects with Suzu. Use precise aim and mobility to support your team in high-pressure moments.",
    "Lifeweaver": "Focus on efficient healing and smart crowd control. Position centrally to maximize your supportive impact while disrupting enemy dives.",
    "Lucio": "Switch between speed boost and healing aura to control the pace of battle. Use sound barriers to block enemy ultimates and aid repositioning.",
    "Mercy": "Deliver high single-target healing and damage boosts. Use Guardian Angel to reposition swiftly and keep your team in the fight.",
    "Moira": "Blend healing with damage by using Biotic Orbs effectively, and use Fade to dodge CC. Balance your dual role to sustain and pressure enemies.",
    "Zenyatta": "Apply Orb of Discord to amplify damage on targets and dish consistent DPS with Orb of Destruction. Provide clutch Transcendence when needed."
}

# ------------------------------------------------------------------
# TEMPLATES
# ------------------------------------------------------------------

# Step 1: Select Enemy Hero 
step1_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Overwatch 2 Counter Picker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body {
            background-color: #405275;
            color: #f0edf2;
            font-family: 'Futura', sans-serif;
        }
        
        .navbar {
            background-color: rgba(0, 0, 0, 0.8);
        }
        
        .card {
            background-color: rgba(0, 0, 0, 0.6);
            border: 2px solid #f99e1a;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(249, 158, 26, 0.5);
        }
        
        .btn-primary {
            background-color: #218ffe;
            border-color: #218ffe;
        }
        
        .btn-primary:hover {
            background-color: #0d6efd;
            border-color: #0d6efd;
        }
        
        .hero-card {
            transition: transform 0.2s;
            cursor: pointer;
            height: 100%;
        }
        
        .hero-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(249, 158, 26, 0.8);
        }
        
        .hero-icon {
            width: 64px;
            height: 64px;
            border-radius: 8px;
            border: 2px solid #fff;
        }
        
        .tank-border {
            border-color: #2980b9;
        }
        
        .damage-border {
            border-color: #c0392b;
        }
        
        .support-border {
            border-color: #27ae60;
        }
        
        .unknown-border {
            border-color: #777;
        }
        
        .effectiveness {
            width: 100%;
            height: 6px;
            background-color: #e74c3c;
            border-radius: 3px;
            margin-top: 5px;
        }
        
        .effectiveness-fill {
            height: 100%;
            background-color: #2ecc71;
            border-radius: 3px;
        }
        
        .filter-btn {
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        .filter-btn.active {
            background-color: #f99e1a;
            border-color: #f99e1a;
        }
        
        .hero-name {
            font-weight: bold;
            margin-top: 5px;
        }
        
        .result-header {
            background: linear-gradient(135deg, #f99e1a, #218ffe);
            color: #fff;
            padding: 1.5rem;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        
        .result-body {
            padding: 1.5rem;
            background-color: rgba(0, 0, 0, 0.7);
            color: #f0edf2;
        }
        
        .hero-weakness {
            background-color: rgba(231, 76, 60, 0.2);
            border-left: 4px solid #e74c3c;
            padding: 10px;
            margin-bottom: 15px;
        }
        
        .tip-card {
            background-color: rgba(52, 152, 219, 0.1);
            border-left: 4px solid #218ffe;
            padding: 10px;
            margin-bottom: 10px;
        }
        
        .synergy-badge {
            background-color: #8e44ad;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        .map-badge {
            background-color: #16a085;
            margin-right: 5px;
            margin-bottom: 5px;
        }
        
        .search-box {
            background-color: rgba(255, 255, 255, 0.2);
            border: 1px solid #f0edf2;
            color: #f0edf2;
        }
        
        .search-box::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        
        .difficulty-meter {
            margin-top: 8px;
        }
        
        .difficulty-pip {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #444;
            margin-right: 4px;
        }
        
        .difficulty-pip.active {
            background-color: #f99e1a;
        }
        
        .difficulty-1 .difficulty-pip.active {
            background-color: #27ae60;  /* Green for easy */
        }
        
        .difficulty-2 .difficulty-pip.active {
            background-color: #f39c12;  /* Orange for medium */
        }
        
        .difficulty-3 .difficulty-pip.active {
            background-color: #e74c3c;  /* Red for hard */
        }
        
        .beginner-friendly-section {
            background-color: rgba(39, 174, 96, 0.2);
            border-left: 4px solid #27ae60;
            padding: 10px;
            margin-bottom: 15px;
        }
        
        .difficulty-filter .btn {
            margin-right: 5px;
        }
        
        @media (max-width: 768px) {
            .hero-card {
                margin-bottom: 15px;
            }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('enemy_selection') }}">
                <span style="color: #f99e1a; font-weight: bold;">OVERWATCH</span> 
                <span style="color: #218ffe;
