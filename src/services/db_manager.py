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
        """テーブルの初期化（初回起動時のみ実行される）"""
        if not self.conn:
            self.connect()
        
        cursor = self.conn.cursor()
        
        # 1. Sessions Table (会話のセッション管理)
        # 再起動しても「どの会話の続きか」を管理します
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        # 2. Messages Table (実際の会話ログ)
        # チャット画面の表示用にテキストをそのまま保存します
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL, -- 'user' or 'ai'
                content TEXT,
                meta_json TEXT, -- 感情やRAG使用ログなどのメタデータ
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        """)
        
        # 3. Memories Table (将来的な「思い出」機能用)
        # 特に重要な情報を要約して保存する場所（今回は枠だけ作成）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                content TEXT,
                importance INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()
        print(f"[Database] Initialized: {self.db_path}")

    # --- Session Methods ---
    def create_session(self, title: str = None) -> int:
        if not title:
            title = datetime.now().strftime("%Y-%m-%d %H:%M の会話")
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sessions (title) VALUES (?)", (title,))
        self.conn.commit()
        return cursor.lastrowid

    def get_sessions(self, limit=20) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_active_session(self) -> Optional[dict]:
        """最後に使っていたセッションを取得（続きから話す用）"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_session_timestamp(self, session_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
        self.conn.commit()

    # --- Message Methods ---
    def add_message(self, session_id: int, role: str, content: str, meta: dict = None):
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else "{}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO messages (session_id, role, content, meta_json)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, meta_json))
        
        self.update_session_timestamp(session_id)
        self.conn.commit()
        return cursor.lastrowid

    def get_messages(self, session_id: int, limit=100) -> List[dict]:
        """チャット画面復元用"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages 
            WHERE session_id = ? 
            ORDER BY created_at ASC
        """, (session_id,))
        
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
