import logging
import datetime
import threading
from datetime import timedelta

logger = logging.getLogger(__name__)

class DiaryGenerator:
    def __init__(self, services_container):
        self.services = services_container
        self.generating = False

    def check_and_generate_diary(self, force=False):
        """
        checks if a diary entry exists for 'yesterday' (logical 4:00 AM start).
        If not, generates it.
        Run this in a separate thread to avoid blocking startup.
        """
        import time
        time.sleep(5) # Wait for Frontend UI to initialize
        if self.generating: return
        
        # Calculate Logical Dates
        # If now is 03:00 (Dec 28), it belongs to Dec 27 cycle.
        # If now is 05:00 (Dec 28), it belongs to Dec 28 cycle.
        now = datetime.datetime.now()
        
        # 1. Determine "Logical Today's Start"
        if now.hour < 4:
            logical_today_start = now.replace(hour=4, minute=0, second=0, microsecond=0) - timedelta(days=1)
        else:
            logical_today_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
            
        # 2. Target Calculation
        if force:
            # Manual: Generate for "TODAY" (Logs so far)
            target_start = logical_today_start
            target_end = datetime.datetime.now() # Until now
        else:
            # Auto: Generate for "YESTERDAY" (Completed cycle)
            target_start = logical_today_start - timedelta(days=1)
            target_end = logical_today_start
        
        # Date string for DB (YYYY-MM-DD representing the start day)
        target_date_str = target_start.strftime("%Y-%m-%d")
        
        logger.info(f"[Diary] Checking diary for {target_date_str} (Force={force}, Range: {target_start} ~ {target_end})")
        
        # 3. Check DB
        if not force and self.services.db_manager.get_diary_by_date(target_date_str):
            logger.info(f"[Diary] Diary for {target_date_str} already exists.")
            return

        # 4. Generate
        self.generating = True
        threading.Thread(target=self._generate_process, args=(target_date_str, target_start, target_end), daemon=True).start()

    def _generate_process(self, date_str, start_dt, end_dt):
        try:
            logger.info(f"[Diary] Generating diary for {date_str}...")
            if hasattr(self.services, 'log_to_debug'):
                self.services.log_to_debug(f"[Diary] {date_str} の日記を執筆中...", "info")
            
            # Fetch logs
            logs = self.services.db_manager.get_logs_in_range(start_dt, end_dt)
            
            if not logs:
                logger.info(f"[Diary] No conversation logs found for {date_str}. Skipping.")
                if hasattr(self.services, 'log_to_debug'):
                     self.services.log_to_debug(f"[Diary] {date_str} の会話ログがないため、日記は作成されませんでした。", "info")
                self.generating = False
                return

            # Format Logs
            log_text = ""
            for l in logs:
                rol = "User" if l['role'] == 'user' else "SoulMate"
                log_text += f"{rol}: {l['content']}\n"
                
            # Generate via AI
            prompt = f"""
[Task]
You are SoulMate. Read the conversation logs from "Yesterday ({date_str})" and write a personal diary entry.
This is NOT a message to the user. It is your private diary.

[Logs]
{log_text}

[Instructions]
- Recap what you talked about with the user.
- Express your honest feelings (happiness, worry, fun).
- Use a warm, personal tone (Persona: SoulMate).
- Length: 200-400 characters approximately.
- Language: Japanese.

[Output Format (JSON)]
{{
    "title": "A short, cute title for this day",
    "content": "Diary content...",
    "emotion": "happy/calm/etc"
}}
"""
            # Use GenAI Client directly for strict JSON (Bypassing AIEngine conversational wrapper)
            from google.genai import types
            client = self.services._ai_engine.client
            model = self.services._ai_engine.reasoning_model
            
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            # Parse Response
            import json
            try:
                response_data = json.loads(response.text)
            except:
                logger.error(f"[Diary] JSON Parse Error. Raw: {response.text}")
                response_data = {}

            if isinstance(response_data, dict):
                title = response_data.get("title", f"{date_str}の日記")
                content = response_data.get("content", "")
                emotion = response_data.get("emotion", "neutral")
            else:
                # Fallback
                title = f"{date_str}の日記"
                content = str(response.text)
                emotion = "neutral"
                
            if content:
                self.services.db_manager.save_diary(date_str, title, content, emotion)
                logger.info(f"[Diary] Saved: {title}")
                
                # System Log
                if hasattr(self.services, 'log_to_debug'):
                    self.services.log_to_debug(f"[Diary] {date_str} の日記を書き終えました: {title}", "success")

        except Exception as e:
            logger.error(f"[Diary] Generation failed: {e}")
        finally:
            self.generating = False
