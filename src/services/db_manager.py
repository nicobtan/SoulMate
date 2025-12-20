import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

# RAG用の chroma.sqlite3 とは別ファイルにします
DB_PATH = "soulmate.db"

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # カラム名でアクセス可能にする

    def init_db(self):
        """Initializes the database table."""
        try:
            if not self.conn:
                self.connect()
            cursor = self.conn.cursor()
            
            # Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT 'New Session',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Messages Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    meta_json TEXT, -- For storing extra data like suggestions
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            """)
            
            # ★追加: マイグレーション (既存DBにカラム追加)
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
            except:
                pass
            
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN is_active BOOLEAN DEFAULT 0")
            except:
                pass
            
            self.conn.commit()
            print("[DatabaseManager] DB Initialized.")
        except Exception as e:
            print(f"[DatabaseManager] DB Init Error: {e}")

    def create_session(self, title="New Session"):
        """Creates a new session, sets it as active, and returns its ID."""
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        
        # Deactivate others
        cursor.execute("UPDATE sessions SET is_active = 0")
        
        cursor.execute("INSERT INTO sessions (title, is_active) VALUES (?, 1)", (title,))
        self.conn.commit()
        return cursor.lastrowid

    # ★更新: 検索(keyword)とフィルタ(favorites_only)に対応
    def get_sessions(self, limit=50, keyword=None, favorites_only=False):
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        
        query = "SELECT DISTINCT s.* FROM sessions s"
        params = []
        conditions = []

        # キーワード検索 (タイトル または メッセージ内容)
        if keyword:
            query += " LEFT JOIN messages m ON s.id = m.session_id"
            conditions.append("(s.title LIKE ? OR m.content LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if favorites_only:
            conditions.append("s.is_favorite = 1")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY s.updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    # ★追加: 削除機能
    def delete_session(self, session_id):
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        try:
            # メッセージを先に削除
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            # セッションを削除
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Delete Error: {e}")
            return False

    # ★追加: お気に入り切替
    def toggle_favorite(self, session_id, is_favorite):
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        val = 1 if is_favorite else 0
        cursor.execute("UPDATE sessions SET is_favorite = ? WHERE id = ?", (val, session_id))
        self.conn.commit()
        return val

    def get_active_session(self) -> Optional[dict]:
        """アクティブなセッションを取得(is_active=1)。なければNone"""
        cursor = self.conn.cursor()
        # まず is_active を見る
        cursor.execute("SELECT * FROM sessions WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_last_message(self):
        """DB内の全履歴の中で、最も新しいメッセージを取得する"""
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_last_session(self):
        """最も最近更新されたセッションを取得する"""
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def set_session_active(self, session_id):
        """指定したセッションをアクティブにし、他を非アクティブにする"""
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET is_active = 0")
        cursor.execute("UPDATE sessions SET is_active = 1 WHERE id = ?", (session_id,))
        self.conn.commit()

    def get_session(self, session_id):
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return cursor.fetchone()

    def update_session_timestamp(self, session_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
        self.conn.commit()

    def update_session_title(self, session_id: int, title: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        self.conn.commit()

    # --- Message Methods ---
    def add_message(self, session_id: int, role: str, content: str, meta: dict = None):
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else "{}"
        cursor = self.conn.cursor()
        query = "INSERT INTO messages (session_id, role, content, meta_json) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (session_id, role, content, meta_json))
        
        self.update_session_timestamp(session_id)
        self.conn.commit()
        return cursor.lastrowid

    def get_messages(self, session_id: int, limit=100) -> List[dict]:
        """チャット画面復元用"""
        cursor = self.conn.cursor()
        query = "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC"
        cursor.execute(query, (session_id,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d.get('meta_json'):
                try:
                    d['meta'] = json.loads(d['meta_json'])
                except:
                    d['meta'] = {}
            results.append(d)
        return results

    # ★追加: 感情記憶のランダム取得 (Emotional Memory Recall)
    def get_random_memory(self, emotion: str = None):
        """ランダムに感情付きの過去ログを1件取得する"""
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        
        query = "SELECT content, meta_json FROM messages WHERE role = 'ai' AND meta_json LIKE '%\"emotion\"%'"
        params = []
        
        if emotion:
           query += " AND meta_json LIKE ?"
           params.append(f'%"{emotion}"%')
        
        query += " ORDER BY RANDOM() LIMIT 1"
        
        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        
        if row:
            d = dict(row)
            try:
                meta = json.loads(d['meta_json'])
                return {"content": d['content'], "emotion": meta.get('emotion')}
            except:
                pass
        return None

    def get_memory_by_emotion(self, emotion: str):
        """指定された感情タグを持つ過去のAIメッセージをランダムに1件取得する"""
        if not self.conn: self.connect()
        cursor = self.conn.cursor()
        
        # metaカラムはJSON文字列なので、json_extractでemotionフィールドを探す
        # SQLiteの RANDOM() でランダム取得
        query = """
            SELECT content, created_at FROM messages 
            WHERE role = 'ai' 
            AND json_extract(meta_json, '$.emotion') = ? 
            ORDER BY RANDOM() LIMIT 1
        """
        cursor.execute(query, (emotion,))
        row = cursor.fetchone()
        
        if row:
            return {"content": row[0], "created_at": row[1]}
        return None
