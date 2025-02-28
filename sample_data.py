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

def generate_sample_data():
    """Generate sample data in the same format as the load_counter_data function"""
    counter_data = SAMPLE_COUNTER_DATA
    enemy_characters = list(counter_data.keys())
    
    heroes_by_role = {
        "Tank": [],
        "Damage": [],
        "Support": [],
        "Unknown": []
    }
    
    for hero, data in counter_data.items():
        role = data["Role"]
        if role in heroes_by_role:
            heroes_by_role[role].append(hero)
    
    for role in heroes_by_role:
        heroes_by_role[role] = sorted(heroes_by_role[role])
    
    return counter_data, enemy_characters, heroes_by_role
