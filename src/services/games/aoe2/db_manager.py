
import sqlite3
import os

class AoE2DatabaseManager:
    def __init__(self, db_path="game_aoe2.db"):
        # Adjust path if running from root
        if not os.path.exists(db_path):
             # Try checking relative to this file if not found in root
             base = os.path.dirname(os.path.abspath(__file__))
             root_db = os.path.join(os.getcwd(), db_path)
             if os.path.exists(root_db):
                 self.db_path = root_db
             else:
                 # Fallback to local (development)
                 self.db_path = db_path
        else:
            self.db_path = db_path
            
        self.ensure_config_table()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def ensure_config_table(self):
        """Ensures the system_config table exists."""
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            # Set defaults if empty
            if conn.execute("SELECT count(*) FROM system_config").fetchone()[0] == 0:
                conn.execute("INSERT INTO system_config (key, value) VALUES (?, ?)", ("vision_interval_sec", "60"))
                conn.execute("INSERT INTO system_config (key, value) VALUES (?, ?)", ("proactive_mode", "true"))
                conn.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)", ("target_player_name", "Player"))
            conn.commit()

    def get_config(self, key, default=None):
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM system_config WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def set_config(self, key, value):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def get_civilizations(self):
        """Returns list of (id, name, help_text)."""
        with self._get_conn() as conn:
            return conn.execute("SELECT * FROM civilizations ORDER BY name").fetchall()

    def get_unit_by_name(self, name):
        """Search unit by name (partial match). Returns dict."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            # Search English Name first
            row = conn.execute("SELECT * FROM units WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
            if not row:
                # Fallback to internal name
                row = conn.execute("SELECT * FROM units WHERE internal_name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
            
            if row:
                return dict(row)
        return None

    def get_unit_by_id(self, unit_id):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM units WHERE id = ?", (unit_id,)).fetchone()
            if row:
                return dict(row)
        return None

    def calculate_damage(self, attacker_id, defender_id):
        """
        Calculates theoretical damage Attacker -> Defender.
        Formula: Max(1, (BaseAttack + Bonus vs Armor Classes) - (Melee/Pierce Armor))
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Get Attacker Stats
            attacker = cursor.execute("SELECT * FROM units WHERE id = ?", (attacker_id,)).fetchone()
            if not attacker: return {"error": "Attacker not found"}
            
            # 2. Get Defender Stats
            defender = cursor.execute("SELECT * FROM units WHERE id = ?", (defender_id,)).fetchone()
            if not defender: return {"error": "Defender not found"}

            # 3. Get Defender's Armor Classes
            defender_classes = cursor.execute("SELECT class_id FROM unit_armor_classes WHERE unit_id = ?", (defender_id,)).fetchall()
            def_class_ids = [row['class_id'] for row in defender_classes]

            # 4. Calculate Attack
            # Note: In data.json, 'Attack' is just one number (usually displayed).
            # Real damage calculation depends on 'Class' of attack matching 'Class' of armor.
            # AoE2 logic: 
            #   Damage = 0
            #   For each Attack Bonus (Class X, Amount A) of Attacker:
            #       If Defender has Armor Class X (Amount B):
            #           Damage += Max(0, A - B)
            #   
            #   Wait, pure "Attack" (Melee/Pierce) is also encoded as a Class in 'Attacks' list usually?
            #   Class 4 = Melee, Class 3 = Pierce.
            #   Let's check 'Attacks' table `unit_attack_bonuses`.
            
            pass
            
            # Let's perform query join logic
            # Sum of (Attacker.Bonus - Defender.Armor) for matching classes
            
            # Get All Attacker Bonuses
            bonuses = cursor.execute("SELECT target_class_id, amount FROM unit_attack_bonuses WHERE unit_id = ?", (attacker_id,)).fetchall()
            
            total_damage = 0
            details = []
            
            base_damage_found = False
            
            for bonus in bonuses:
                cls_id = bonus['target_class_id']
                atk_amt = bonus['amount']
                
                # Check if defender has this class
                # Need to find Armor Amount for this class
                armor_row = cursor.execute("SELECT amount FROM unit_armor_classes WHERE unit_id = ? AND class_id = ?", 
                                           (defender_id, cls_id)).fetchone()
                
                if armor_row:
                    armor_amt = armor_row['amount']
                    dmg = max(0, atk_amt - armor_amt)
                    details.append(f"Class {cls_id}: {atk_amt}(Atk) - {armor_amt}(Arm) = {dmg}")
                    total_damage += dmg
                    
                    if cls_id == 4: base_damage_found = True # Melee
                    if cls_id == 3: base_damage_found = True # Pierce

            # Fallback (If logic mismatch):
            # If total_damage is 0, maybe standard calculation applies? 
            # Usually standard attack is Class 4 (Melee) or Class 3 (Pierce).
            # If Attacker has standard attack and Defender has standard armor.
            
            return {
                "attacker": attacker['name'],
                "defender": defender['name'],
                "total_damage": max(1, total_damage), # Minimum 1 damage usually
                "details": details
            }
            
        finally:
            conn.close()

    def log_match(self, my_civ, enemy_civ, result, map_name):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO match_logs (my_civ, enemy_civ, result, map_name) VALUES (?, ?, ?, ?)",
                         (my_civ, enemy_civ, result, map_name))
            conn.commit()

    def get_recent_matches(self, limit=5):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM match_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

    def find_best_counters(self, target_unit_id, limit=3):
        """
        Finds the best counter units against the specified target unit.
        Logic: Sum of Attack Bonuses of Candidate vs Target's Armor Classes.
        Returns list of dicts: {'unit': unit_name, 'score': total_bonus}
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Get Target's Armor Classes
            target_classes = cursor.execute("SELECT class_id FROM unit_armor_classes WHERE unit_id = ?", (target_unit_id,)).fetchall()
            target_class_ids = [row['class_id'] for row in target_classes]
            
            if not target_class_ids:
                return []

            # 2. Find Candidates with Attack Bonus vs these classes
            # We want: Candidate Unit Name, Sum(Bonus Amount)
            # SQL: Join units and unit_attack_bonuses
            
            placeholders = ','.join('?' for _ in target_class_ids)
            query = f"""
                SELECT 
                    u.name as unit_name, 
                    SUM(b.amount) as total_bonus
                FROM unit_attack_bonuses b
                JOIN units u ON b.unit_id = u.id
                WHERE b.target_class_id IN ({placeholders})
                GROUP BY u.id
                ORDER BY total_bonus DESC
                LIMIT ?
            """
            
            params = target_class_ids + [limit]
            results = cursor.execute(query, params).fetchall()
            
            counters = []
            for row in results:
                counters.append({
                    "unit": row['unit_name'],
                    "score": row['total_bonus']
                })
                
            return counters
            
        finally:
            conn.close()
