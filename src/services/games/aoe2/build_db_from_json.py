
import sqlite3
import requests
import json
import os
import time

# Constants
DATA_JSON_URL = "https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/data.json"
STRINGS_JSON_URL = "https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/master/data/locales/en/strings.json" # Assumption
DB_PATH = "game_aoe2.db"

def fetch_json(url):
    print(f"Downloading {url}...")
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def init_db(conn):
    cursor = conn.cursor()
    
    # Civilizations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS civilizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            help_text TEXT
        )
    ''')
    
    # Units
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY,
            internal_name TEXT,
            name TEXT,
            hp INTEGER,
            attack INTEGER,
            melee_armor INTEGER,
            pierce_armor INTEGER,
            range INTEGER,
            reload_time REAL,
            speed REAL,
            line_of_sight INTEGER
        )
    ''')
    
    # Costs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unit_costs (
            unit_id INTEGER,
            resource_type TEXT,
            amount INTEGER,
            FOREIGN KEY(unit_id) REFERENCES units(id)
        )
    ''')
    
    # Attack Bonuses (Attacks list in JSON)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unit_attack_bonuses (
            unit_id INTEGER,
            target_class_id INTEGER,
            amount INTEGER,
            FOREIGN KEY(unit_id) REFERENCES units(id)
        )
    ''')
    
    # Armor Classes (Armours list in JSON)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unit_armor_classes (
            unit_id INTEGER,
            class_id INTEGER,
            amount INTEGER,
            FOREIGN KEY(unit_id) REFERENCES units(id)
        )
    ''')
    
    # Match Logs (For user history)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            my_civ TEXT,
            enemy_civ TEXT,
            map_name TEXT,
            result TEXT,
            memo TEXT
        )
    ''')
    
    conn.commit()

def process_data(data, strings, conn):
    cursor = conn.cursor()
    
    # 1. Civilizations
    # civ_names key is name, value is ID (string). 
    # But wait, looking at JSON structure again: 
    # "civ_names": { "Britons": "10271", ... } -> 10271 is likely String ID.
    # The JSON doesn't list Civ "IDs" (internal numeric IDs) easily in 'civ_names'.
    # But usually Civs have IDs.
    # For now, we will store Name.
    
    print("Processing Civilizations...")
    civ_names = data.get("civ_names", {})
    civ_help = data.get("civ_helptexts", {})
    
    for civ_name, name_str_id in civ_names.items():
        help_str_id = civ_help.get(civ_name)
        help_text = strings.get(str(help_str_id), "") if strings and help_str_id else ""
        
        # Insert
        try:
            cursor.execute("INSERT OR IGNORE INTO civilizations (name, help_text) VALUES (?, ?)", 
                           (civ_name, help_text))
        except Exception as e:
            print(f"Error inserting civ {civ_name}: {e}")

    # 2. Units
    print("Processing Units...")
    units_data = data.get("data", {}).get("units", {})
    
    for uid, u in units_data.items():
        try:
            unit_id = int(uid)
            internal_name = u.get("internal_name", f"Unknown_{uid}")
            
            # Resolve Name
            name_str_id = u.get("LanguageNameId")
            display_name = strings.get(str(name_str_id), internal_name) if strings else internal_name
            
            hp = u.get("HP", 0)
            attack = u.get("Attack", 0)
            melee_armor = u.get("MeleeArmor", 0)
            pierce_armor = u.get("PierceArmor", 0)
            range_val = u.get("Range", 0)
            reload_time = u.get("ReloadTime", 0)
            speed = u.get("Speed", 0)
            los = u.get("LineOfSight", 0)
            
            cursor.execute('''
                INSERT OR REPLACE INTO units 
                (id, internal_name, name, hp, attack, melee_armor, pierce_armor, range, reload_time, speed, line_of_sight)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (unit_id, internal_name, display_name, hp, attack, melee_armor, pierce_armor, range_val, reload_time, speed, los))
            
            # Costs
            costs = u.get("Cost", {})
            for res, amount in costs.items():
                cursor.execute("INSERT INTO unit_costs (unit_id, resource_type, amount) VALUES (?, ?, ?)",
                               (unit_id, res, amount))
            
            # Attack Bonuses (Attacks)
            # JSON format: "Attacks": [{"Amount": 1, "Class": 27}, ...]
            attacks = u.get("Attacks", [])
            for att in attacks:
                cls_id = att.get("Class")
                amount = att.get("Amount")
                cursor.execute("INSERT INTO unit_attack_bonuses (unit_id, target_class_id, amount) VALUES (?, ?, ?)",
                               (unit_id, cls_id, amount))
            
            # Armor Classes (Armours)
            # JSON format: "Armours": [{"Amount": 0, "Class": 4}, ...] 
            armors = u.get("Armours", [])
            for arm in armors:
                cls_id = arm.get("Class")
                amount = arm.get("Amount")
                cursor.execute("INSERT INTO unit_armor_classes (unit_id, class_id, amount) VALUES (?, ?, ?)",
                               (unit_id, cls_id, amount))
                               
        except Exception as e:
            print(f"Error processing unit {uid}: {e}")

    conn.commit()

def main():
    print("--- Starting AoE2 Database Build ---")
    
    # 1. Fetch Data
    data = fetch_json(DATA_JSON_URL)
    if not data:
        print("CRITICAL: Failed to download data.json")
        return

    # 2. Fetch Strings (Optional but better)
    strings = fetch_json(STRINGS_JSON_URL)
    if not strings:
        print("WARNING: Failed to download strings.json. Using internal names.")
    else:
        print("Strings loaded.")

    # 3. Create DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH) # Clean rebuild
        
    conn = sqlite3.connect(DB_PATH)
    
    try:
        init_db(conn)
        process_data(data, strings, conn)
        print("--- Database Build Complete ---")
        
        # Verification
        count = conn.execute("SELECT count(*) FROM units").fetchone()[0]
        print(f"Total Units Inserted: {count}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
