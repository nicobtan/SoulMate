import json
import os
from src.services.db_manager import DatabaseManager

HISTORY_FILE = "history.json"

class MigrationService:
    def __init__(self, db: DatabaseManager):
        self.db = db

import json
import os
from src.services.db_manager import DatabaseManager

HISTORY_FILE = "history.json"
HISTORY_JSONL = "logs/chat_history.jsonl"

class MigrationService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def migrate_json_to_db(self):
        """history.jsonまたは(logs/chat_history.jsonl)があれば読み込み、未保存ならDBに格納してファイルをリネームする"""
        
        migrated_count = 0
        
        # 1. Standard history.json (List format)
        if os.path.exists(HISTORY_FILE):
            print(f"[Migration] Found {HISTORY_FILE}. Importing to DB...")
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)

                if history:
                    session_id = self.db.create_session("インポートされた会話履歴 (JSON)")
                    for msg in history:
                        role = msg.get("role")
                        content = msg.get("content") or msg.get("text")
                        if role and content:
                            self.db.add_message(session_id, role, content)
                            migrated_count += 1
                    
                os.rename(HISTORY_FILE, f"{HISTORY_FILE}.bak")
                print(f"[Migration] JSON Import Success: {migrated_count} messages.")
            except Exception as e:
                print(f"[Migration] JSON Error: {e}")

        # 2. JSONL Log (Line format) - logs/chat_history.jsonl
        # User's current conversation is likely here.
        if os.path.exists(HISTORY_JSONL):
            print(f"[Migration] Found {HISTORY_JSONL}. Importing to DB...")
            try:
                with open(HISTORY_JSONL, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if lines:
                    session_id = self.db.create_session("インポートされた会話履歴 (Log)")
                    count = 0
                    for line in lines:
                        try:
                            entry = json.loads(line)
                            # Entry keys: user, ai, timestamp
                            if "user" in entry and entry["user"]:
                                self.db.add_message(session_id, "user", entry["user"])
                                count += 1
                            if "ai" in entry and entry["ai"]:
                                self.db.add_message(session_id, "ai", entry["ai"])
                                count += 1
                        except:
                            continue
                            
                    migrated_count += count
                    
                # Rename to prevent re-import (or keep as backup?)
                # Rename is safer to avoid duplicates on every boot.
                # But since it's a log, maybe we should archive it?
                # Rename effectively archives it from the active path.
                os.rename(HISTORY_JSONL, f"{HISTORY_JSONL}.bak")
                print(f"[Migration] JSONL Import Success: {count} messages.")

            except Exception as e:
                print(f"[Migration] JSONL Error: {e}")

        if migrated_count == 0:
            print("[Migration] No pending history files found.")
