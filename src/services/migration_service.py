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
                    # --- Title Generation ---
                    first_user_msg = next((msg for msg in history if msg.get("role") == "user"), None)
                    if first_user_msg:
                        raw_text = first_user_msg.get("content") or first_user_msg.get("text") or ""
                        # Limit to ~20 chars
                        title = raw_text[:20] + "..." if len(raw_text) > 20 else raw_text
                        if not title: title = "会話履歴"
                    else:
                        title = "インポートされた会話履歴 (JSON)"

                    session_id = self.db.create_session(title)
                    for msg in history:
                        role = msg.get("role")
                        content = msg.get("content") or msg.get("text")
                        meta = msg.get("meta", {})
                        if role and content:
                            self.db.add_message(session_id, role, content, meta=meta)
                            migrated_count += 1
                    
                os.rename(HISTORY_FILE, f"{HISTORY_FILE}.bak")
                print(f"[Migration] JSON Import Success: {migrated_count} messages as '{title}'.")
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
                    # --- 重複チェックロジック ---
                    # ファイルの最後の有効な行を取得
                    last_entry = None
                    for line in reversed(lines):
                        try:
                            last_entry = json.loads(line)
                            if "user" in last_entry or "ai" in last_entry or "text" in last_entry:
                                break
                        except:
                            continue
                    
                    # DBの最新ログを取得
                    last_db_msg = self.db.get_last_message()
                    
                    is_duplicate = False
                    if last_entry and last_db_msg:
                        # 内容比較 (改行などはnormalizeして比較)
                        file_content = (last_entry.get("ai") or last_entry.get("user") or last_entry.get("text") or "").strip()
                        db_content = (last_db_msg.get("content") or "").strip()
                        
                        if file_content and file_content == db_content:
                            is_duplicate = True
                            print("[Migration] Duplicate detected (Last message matches). Skipping import.")

                    if not is_duplicate:
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
                        print(f"[Migration] JSONL Import Success: {count} messages.")
                    
                # Rename to prevent re-import (or keep as backup?)
                # Rename is safer to avoid duplicates on every boot.
                # But since it's a log, maybe we should archive it?
                # Rename effectively archives it from the active path.
                try:
                    os.rename(HISTORY_JSONL, f"{HISTORY_JSONL}.bak")
                except Exception as e:
                    print(f"[Migration] Rename failed: {e}")

            except Exception as e:
                print(f"[Migration] JSONL Error: {e}")

        if migrated_count == 0:
            print("[Migration] No pending history files found.")

    def sync_jsonl_to_db(self):
        """memory/chat_history.jsonl の内容を、現在のアクティブなセッションに同期（マージ）する"""
        from src.services.history_manager import HistoryManager
        hm = HistoryManager()
        
        # 1. JSONLから最新のメッセージ履歴を取得
        json_history = hm.get_session_history(limit=100)
        if not json_history:
            return
            
        # 2. DBのアクティブセッションを取得
        active_sess = self.db.get_active_session()
        if not active_sess:
            return
        
        session_id = active_sess['id']
        # DB側の既存メッセージを取得（重複チェック用）
        db_messages = self.db.get_messages(session_id)
        
        # 比較用のセットを作成 (role + content)
        existing_msgs = { (m['role'], m['content'].strip()) for m in db_messages }
        
        added_count = 0
        for entry in json_history:
            role = entry.get('role')
            content = entry.get('content', '').strip()
            
            if not role or not content:
                continue
                
            # 重複していなければ追加
            if (role, content) not in existing_msgs:
                self.db.add_message(session_id, role, content)
                added_count += 1
                # 追加したものをセットにも入れる（連続追加時の重複防止）
                existing_msgs.add((role, content))
                
        if added_count > 0:
            print(f"[Migration] Synced {added_count} messages from JSONL to active session {session_id}.")
        else:
            print("[Migration] SQLite is already up to date with JSONL.")

    def fix_legacy_titles(self):
        """
        不適切なタイトル（デフォルト名や内部コマンド由来）を持つセッションを、
        実際の会話内容に基づいてリネームする
        """
        print("[Migration] Checking for bad session titles...")
        import sqlite3
        
        if not self.db.conn:
            self.db.connect()
            
        cursor = self.db.conn.cursor()
        
        cursor.execute("""
            SELECT id FROM sessions 
            WHERE title LIKE 'インポートされた会話履歴%' 
               OR title LIKE '[Situation]%'
               OR title LIKE '無題の会話'
        """)
        rows = cursor.fetchall()
        
        if not rows:
            return

        updated_count = 0
        for row in rows:
            session_id = row[0]
            if isinstance(session_id, sqlite3.Row): session_id = session_id['id']
            
            cursor.execute("""
                SELECT role, content FROM messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC LIMIT 10
            """, (session_id,))
            messages = cursor.fetchall()
            
            new_title = None
            for msg in messages:
                role, content = msg[0], msg[1]
                if not content or content.strip().startswith("["): continue
                if role == 'user':
                    new_title = content
                    break
                if role == 'ai' and not new_title:
                    new_title = f"AI: {content}"
            
            if new_title:
                clean_title = new_title.replace('\n', ' ').strip()
                final_title = clean_title[:20] + "..." if len(clean_title) > 20 else clean_title
                cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (final_title, session_id))
                updated_count += 1
        
        self.db.conn.commit()
        if updated_count > 0:
            print(f"[Migration] Fixed titles for {updated_count} sessions.")

    def clean_internal_logs(self):
        """内部システムプロンプトをDBから削除する"""
        print("[Migration] Cleaning internal system prompts from DB...")
        if not self.db.conn:
            self.db.connect()
        cursor = self.db.conn.cursor()
        cursor.execute("""
            DELETE FROM messages 
            WHERE role = 'user' 
            AND (content LIKE '[Situation]%' OR content LIKE '[System]%' OR content LIKE '[Grounding Instruction]%')
        """)
        deleted_count = cursor.rowcount
        self.db.conn.commit()
        if deleted_count > 0:
            print(f"[Migration] Deleted {deleted_count} internal prompt messages.")
            self.fix_legacy_titles()

