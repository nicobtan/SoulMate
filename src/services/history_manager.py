import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages chat history in JSONL format. 
    Acts as a persistent backup/intermediate storage between app sessions.
    """
    def __init__(self, log_dir="memory"):
        base_dir = os.getcwd()
        self.log_dir = os.path.join(base_dir, log_dir)
        
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except Exception as e:
                print(f"[HistoryManager] Failed to create dir: {e}")

        # Standard file: memory/chat_history.jsonl
        self.history_file = os.path.join(self.log_dir, "chat_history.jsonl")
        print(f"[HistoryManager] Initialized. Path: {self.history_file}")
        
    def add_message(self, role: str, content: str):
        """Append a message to the JSONL history file with a timestamp."""
        try:
            timestamp = datetime.now().isoformat()
            entry = {
                "timestamp": timestamp,
                "role": role,
                "content": content
            }
            with open(self.history_file, 'a', encoding='utf-8') as f:
                json_line = json.dumps(entry, ensure_ascii=False)
                f.write(json_line + "\n")
        except Exception as e:
            logger.error(f"Failed to save message to JSONL: {e}")

    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Readsstructured history from JSONL. 
        Supports legacy formats (Pattern A: role/content, Pattern B: user_message/ai_response).
        """
        print(f"[HistoryManager] Reading from: {self.history_file}")
        history = []
        
        if not os.path.exists(self.history_file):
            return history
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Process in reverse (Newest -> Oldest)
            for line in reversed(lines):
                if len(history) >= limit:
                    break
                try:
                    data = json.loads(line)
                    
                    # 1. New Structured Format (role, content, timestamp)
                    if "role" in data and "content" in data:
                        history.insert(0, {
                            "role": data["role"],
                            "content": data["content"],
                            "timestamp": data.get("timestamp")
                        })
                        continue

                    # 2. Legacy Format (user_message, ai_response)
                    # Handle AI first (prepending to keep order)
                    ai_text = data.get("ai_response") or data.get("ai")
                    if ai_text:
                        history.insert(0, {
                            "role": "ai",
                            "content": ai_text,
                            "timestamp": data.get("timestamp") or data.get("created_at")
                        })
                    
                    user_text = data.get("user_message") or data.get("user")
                    if user_text:
                        history.insert(0, {
                            "role": "user",
                            "content": user_text,
                            "timestamp": data.get("timestamp") or data.get("created_at")
                        })
                            
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            
        print(f"[HistoryManager] Loaded {len(history)} items.")
        return history

