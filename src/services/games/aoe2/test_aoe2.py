
from db_manager import AoE2DatabaseManager
import os

def test_damage_calc():
    print("--- Testing AoE2 Damage Calculation ---")
    
    # Path might need adjustment depending on where we run this
    db_path = "game_aoe2.db"
    if not os.path.exists(db_path):
         # Try parent dir or root
         root_db = os.path.join(os.getcwd(), db_path)
         if os.path.exists(root_db):
             db_path = root_db
         else:
             print("DB not found.")
             return

    mgr = AoE2DatabaseManager(db_path)
    
    # 1. Get Unit IDs
    # Halberdier (HALBD)
    halb = mgr.get_unit_by_name("HALBD")
    if not halb:
        print("Halberdier not found (try internal name HALBD)")
        return
        
    # Paladin (PALAD)
    paladin = mgr.get_unit_by_name("PALAD")
    if not paladin:
        print("Paladin not found")
        return
        
    print(f"Attacker: {halb['name']} (ID: {halb['id']})")
    print(f"Defender: {paladin['name']} (ID: {paladin['id']})")
    
    # 2. Calculate Damage
    result = mgr.calculate_damage(halb['id'], paladin['id'])
    
    print("\n[Calculation Result]")
    print(f"Total Damage: {result['total_damage']}")
    print("Details:")
    for d in result['details']:
        print(f" - {d}")
        
    # Expected: Halberdier has huge bonus vs Cavalry (Class 8?)
    # Paladin has Armor vs Infantry?
    
    # 3. Test Match Log
    print("\n--- Testing Match Log ---")
    mgr.log_match("Franks", "Britons", "Win", "Arabia")
    recent = mgr.get_recent_matches()
    print(f"Match Logged: {len(recent)} entries")
    for r in recent:
        print(f" - {r['my_civ']} vs {r['enemy_civ']} on {r['map_name']}: {r['result']}")

if __name__ == "__main__":
    test_damage_calc()
