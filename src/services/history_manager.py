import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, log_dir="memory"): # 保存先を memory に統一
        base_dir = os.getcwd()
        self.log_dir = os.path.join(base_dir, log_dir)
        
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except Exception as e:
                print(f"[HistoryManager] Failed to create dir: {e}")

        # JSONL形式で統一
        self.history_file = os.path.join(self.log_dir, "chat_history.jsonl")
        print(f"[HistoryManager] Initialized. Path: {self.history_file}")
        
    def add_message(self, role: str, content: str):
        """会話を保存するメソッド（念のため追加）"""
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                # 統一フォーマットで保存
                json_line = json.dumps({"role": role, "content": content}, ensure_ascii=False)
                f.write(json_line + "\n")
        except Exception as e:
            logger.error(f"Failed to save message: {e}")

    def get_session_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """履歴を読み込む（新旧フォーマット対応版）"""
        print(f"[HistoryManager] Reading from: {self.history_file}")
        history = []
        
        if not os.path.exists(self.history_file):
            return history
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 新しい順に処理
            for line in reversed(lines):
                if len(history) >= limit:
                    break
                try:
                    data = json.loads(line)
                    
                    # Pattern A: Standard new format (role, content)
                    if "role" in data and "content" in data:
                        history.insert(0, {
                            "role": data["role"],
                            "text": data["content"]
                        })
                        continue

                    # Pattern B: Legacy format (user_message, ai_response) OR (user, ai)
                    # We handle all variations here.
                    
                    # 1. AI Response
                    # Check for 'ai_response' OR 'ai'
                    ai_text = data.get("ai_response") or data.get("ai")
                    if ai_text:
                        if len(history) < limit:
                            history.insert(0, {
                                "role": "ai",
                                "text": ai_text
                            })

                    # 2. User Message
                    # Check for 'user_message' OR 'user'
                    user_text = data.get("user_message") or data.get("user")
                    if user_text:
                         if len(history) < limit:
                            history.insert(0, {
                                "role": "user",
                                "text": user_text
                            })
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            
        print(f"[HistoryManager] Loaded {len(history)} items.")
        return history

        """
        Initialize HistoryManager pointing to the memory directory.
        """
        # Robust absolute path resolution
        base_dir = os.getcwd()
        self.memory_dir = os.path.join(base_dir, memory_dir)
        
        # Ensure directory exists
        if not os.path.exists(self.memory_dir):
            try:
                os.makedirs(self.memory_dir)
                print(f"[HistoryManager] Created memory directory: {self.memory_dir}")
            except Exception as e:
                print(f"[HistoryManager] Failed to create memory dir: {e}")

        # Primary file: memory/chat_history.jsonl
        self.history_file = os.path.join(self.memory_dir, "chat_history.jsonl")
        print(f"[HistoryManager] Initialized. DB Path: {self.history_file}")
        
    def get_session_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent chat history for session restoration.
        Format: [{"role": "user", "text": "..."}, {"role": "ai", "text": "..."}]
        """
        print(f"[HistoryManager] Reading history from: {self.history_file}")
        
        history = []
        if not os.path.exists(self.history_file):
            print(f"[HistoryManager] File not found: {self.history_file}")
            # Try fallback to 'logs' if memory not found (Optional robustness)
            fallback = os.path.join(os.getcwd(), "logs", "chat_history.jsonl")
            if os.path.exists(fallback):
               print(f"[HistoryManager] Fallback to logs: {fallback}")
               self.history_file = fallback
            else:
               return history
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"[HistoryManager] Found {len(lines)} lines.")
                
                # Process lines in reverse (Newest -> Oldest)
                count = 0
                for line in reversed(lines):
                    if count >= limit:
                        break
                        
                    try:
                        data = json.loads(line)
                        
                        # Logic: We are prepending to 'history' list (insert at 0).
                        # To maintain [User, AI] order in the final list for a single interaction line:
                        # 1. Insert AI first (becomes [AI, ...])
                        # 2. Insert User (becomes [User, AI, ...])
                        
                        # 1. AI Response
                        if "ai_response" in data and data["ai_response"]:
                            if count < limit:
                                history.insert(0, {
                                    "role": "ai",
                                    "text": data["ai_response"]
                                })
                                count += 1
                        
                        # 2. User Message
                        if "user_message" in data and data["user_message"]:
                            if count < limit:
                                history.insert(0, {
                                    "role": "user",
                                    "text": data["user_message"]
                                })
                                count += 1
                                
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to read session history: {e}")
            print(f"[HistoryManager] Error reading history: {e}")
            
        print(f"[HistoryManager] Returning {len(history)} messages.")
        return history
