
import sys
import os

# Adjust path to find modules
sys.path.append(os.getcwd())

from src.services.games.aoe2.db_manager import AoE2DatabaseManager
from src.services.games.aoe2.rival_scout import RivalScout

def main():
    user_id = "11756313" # NicoBtan
    
    print("--- Rival Scout System Start ---")
    
    # Init
    mgr = AoE2DatabaseManager()
    scout = RivalScout(mgr)
    
    # 1. Setup DB
    scout.ensure_tables()
    
    # 2. Fetch
    print("Fetching history since 2025...")
    matches = scout.fetch_matches(user_id, target_year=2025)
    print(f"Fetched {len(matches)} matches (Filtered by Custom, since 2025).")
    
    # 3. Sync
    if matches:
        scout.sync_db(matches)
    else:
        print("No matches found matching criteria.")

    # 4. Report
    print("\n--- Current Top Rivals ---")
    with mgr._get_conn() as conn:
        rows = conn.execute("SELECT name, total_matches, last_met FROM rivals ORDER BY total_matches DESC LIMIT 5").fetchall()
        for r in rows:
            print(f"Rival: {r[0]} | Matches: {r[1]} | Last Met: {r[2]}")

if __name__ == "__main__":
    main()
