
import sqlite3
import os

DB_PATH = "game_aoe2.db"

def init_user_profile():
    print(f"--- Initializing User Profile in {DB_PATH} ---")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Drop Old Table (Schema Change)
        print("Dropping old table if exists...")
        cursor.execute("DROP TABLE IF EXISTS aoe2_player_profile")

        # 2. Create New Table
        print("Creating table 'aoe2_player_profile' (v2)...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aoe2_player_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                steam_name TEXT UNIQUE,
                elo_rating INTEGER DEFAULT 1000,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. Insert Seed Data
        print("Inserting seed data for 'NicoBtan'...")
        try:
            cursor.execute('''
                INSERT INTO aoe2_player_profile (steam_name, elo_rating, note)
                VALUES (?, ?, ?)
            ''', ("NicoBtan", 1000, "Balance"))
        except Exception as e:
            print(f"Insert warning: {e}")

        conn.commit()
        
        # 4. Verify
        print("\n--- Verification: Loaded Profiles ---")
        rows = cursor.execute("SELECT * FROM aoe2_player_profile").fetchall()
        for row in rows:
            print(row)
            
    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_user_profile()
