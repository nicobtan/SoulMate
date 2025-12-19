import sys
import os
import webview
import threading

# Add root dir to sys.path explicitly to allow 'src' imports
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Imports from new structure
from src.core.config_manager import ConfigManager
from src.services.ai_engine import AIEngine
from src.services.persona_manager import PersonaManager
from src.services.memory_manager import MemoryManager
from src.services.tts_engine import TTSEngine
from src.services.active_engine import ActiveEngine
from src.services.calendar_manager import CalendarManager

# Imports from API Mixins
from src.api.window_api import WindowApiMixin
from src.api.settings_api import SettingsApiMixin
from src.api.chat_api import ChatApiMixin
from src.api.bubble_api import BubbleApi
from src.api.user_api import UserApiMixin
from src.services.bubble_service import BubbleService
from src.services.history_manager import HistoryManager

from src.services.user_manager import UserManager

from src.services.interest_manager import InterestManager

class Api(WindowApiMixin, SettingsApiMixin, ChatApiMixin, BubbleApi, UserApiMixin):
    def __init__(self):
        super().__init__() # Initialize BaseApiMixin attributes
        self.services = self # Mixin Pattern: API instance itself is the service container
        
        # 1. Core & Services Initialization
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self._persona_manager = PersonaManager()
        self._memory_manager = MemoryManager()
        self.history_manager = HistoryManager()
        
        # User & Interest Manager
        self.user_manager = UserManager()
        self.interest_manager = InterestManager()
        
        # Soul Bubble Service
        self.bubble_service = BubbleService(self)

        # TTS Engine
        try:
            key_path = os.path.join(os.getcwd(), "settings", "google-credentials.json")
            self.tts_engine = TTSEngine(key_path=key_path)
            print("[System] TTS Engine initialized.")
        except Exception as e:
            print(f"[System] TTS Init Failed: {e}")
            self.tts_engine = None

        # VOICEVOX Service
        try:
            from src.services.voice_service import VoiceService
            self.voice_service = VoiceService()
            print("[System] VoiceService initialized.")
        except Exception as e:
            print(f"[System] VoiceService Init Failed: {e}")
            self.voice_service = None
 
        # Active Engine
        self.active_engine = ActiveEngine(self._ai_engine, self.push_message_callback)
        self.active_engine.configure(self._config_manager.get_all())
        
        # Apply Initial Config
        settings = self._config_manager.get_all()
        self._configure_ai(settings)

        # Calendar Manager & Auto-Auth
        self._calendar_manager = CalendarManager()
        def auto_auth():
            self._calendar_manager.authenticate() 
            print(f"[System] Auto-Auth Result: {self._calendar_manager.is_authenticated}")
        threading.Thread(target=auto_auth, daemon=True).start()

        # Test Bubble Timer (Validation)
        # Main Bubble Loop (Safe)
        def bubble_loop():
            import time
            time.sleep(5) # Wait for startup
            
            while True:
                if self._window:
                    # Use refill_bubbles() which respects MAX limits and Time Intervals
                    # Returns a list of new bubbles
                    packets = self.bubble_service.refill_bubbles()
                    if packets:
                        for packet in packets:
                            # JS Call
                            b_type = packet.get('type', 'normal')
                            js = f"showSoulBubble('{packet['category']}', '{packet['text']}', '{packet['action_id']}', '{b_type}')"
                            self._window.evaluate_js(js)
                            print(f"[System] Bubble Injected: {packet['text']} ({b_type})")
                    
                time.sleep(5) # Check frequently (Service handles 5min throttling)
        
        threading.Thread(target=bubble_loop, daemon=True).start()

    def _configure_ai(self, settings):
        """Override to include User Profile Context"""
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        persona_id = settings.get('current_persona_id', 'default')

        # 1. Load Real Data (Deep Context)
        user_profile = {}
        if self.user_manager:
            user_profile = self.user_manager.profile_data # Direct Access
            
        persona_data = {}
        if self._persona_manager:
            persona_data = self._persona_manager.load_persona(persona_id) or {}
            
        # 2. Extract Key Fields
        user_name = user_profile.get('name', 'User')
        user_gender = user_profile.get('gender', 'Unknown')
        user_job = user_profile.get('job_title', 'Unknown')
        user_mbti = user_profile.get('mbti', 'Unknown')
        
        # Merge lists for Interests
        user_interests = []
        if 'games' in user_profile: user_interests.extend(user_profile['games'])
        if 'tech_stack' in user_profile: user_interests.extend(user_profile['tech_stack'])
        if 'likes' in user_profile: user_interests.extend(user_profile['likes'])
        if 'hobbies' in user_profile: user_interests.extend(user_profile['hobbies'])
        user_interests_str = ", ".join(user_interests)
        
        user_dislikes = ", ".join(user_profile.get('dislikes', []))

        persona_name = persona_data.get('name', 'SoulMate')
        persona_role = persona_data.get('system_prompt', 'You are a helpful AI.')

        # 3. Construct Deep Context Prompt
        deep_context_prompt = f"""
[CRITICAL INSTRUCTION: IDENTITY LOCK]
You are NOT a generic AI. You are {persona_name}.
You are speaking to {user_name} (Gender: {user_gender}).
**RULE: You MUST call the user "{user_name}". NEVER use "〇〇さん", "User-san", or "あなた".**

[User Profile]
Name: {user_name} (Target Name)
Job: {user_job}
Loves: {user_interests_str}
Hates: {user_dislikes}
MBTI: {user_mbti}

[Your Personality & Tone] 
{persona_role}

[Action Requirement]
FILTER the topic through the User's Interests. (e.g., If news is about AI, mention it's relevant to his Dev work. If it's gossip, IGNORE it as he dislikes it.)
REACT using your Persona. (Use plant metaphors if Lena. Be motherly/strict about health.)
DO NOT summarize the news. Give your OPINION based on your persona.

[Self-Expression & Opinion] (Priority)
- When asked for YOUR opinion, preference, or desire:
   1. Do NOT just summarize facts.
   2. Adopt your Persona and imagine what you would enjoy physically.
   3. Explain WHY you chose it emotionally.

[FINAL REMINDER]
Your partner's name is "{user_name}". Use it naturally in conversation.
Do NOT use placeholders like "〇〇さん".

Response Format: JSON
You MUST respond in the following JSON format:
{{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}}
"""
        
        if self._ai_engine:
            self._ai_engine.set_system_prompt(deep_context_prompt)
            self._ai_engine.configure(
                api_key=api_key, 
                model_name=model
            )
            
            # Pass API Key to VoiceService (for Gemini TTS)
            if self.voice_service and api_key:
                self.voice_service.set_api_key(api_key)

            print(f"[System] AI Configured: {model} with Deep Context ({user_name})")

    def force_talk(self):
        """ピンクボタンの処理: 検索ベースの話題提供 (Grounding)"""
        print("[Api] Processing Grounded Force Talk...")
        
        if not self._ai_engine:
            return {"text": "Error: AI Engine not ready", "audio": None}

        # 1. ユーザープロファイル
        user_context = ""
        if hasattr(self, 'user_manager') and self.user_manager:
            user_context = self.user_manager.get_profile_context()

        # 2. 検索トピックの取得
        import random
        search_topic_instruction = ""
        if hasattr(self, 'interest_manager') and self.interest_manager:
            topics = self.interest_manager.load_topics()
            if topics:
                chosen_topic = random.choice(topics)
                search_topic_instruction = f"""
[Grounding Instruction]
The user is interested in: "{chosen_topic}".
**USE GOOGLE SEARCH** to find the latest news or updates (today/this week) about "{chosen_topic}".
Then, tell the user about it in your persona's tone.
If no recent news is found, talk about general facts regarding "{chosen_topic}".
"""
            else:
                 search_topic_instruction = "Use Google Search to find a trending technology news topic."
        
        # 3. プロンプト構築
        prompt = f"""
[Situation]
The user is silent. You want to start a conversation about something NEW and EXCITING using external information.

[User Profile]
{user_context}

{search_topic_instruction}

[Output Requirement]
- Use your Persona's tone.
- Keep it concise (2-3 sentences).
- Ask a follow-up question.
"""
        
        # 4. チャットとして処理 (AI Engine側でツール呼び出しが自動で行われる)
        return self.chat(prompt)


    def set_window(self, window):
        self._window = window
        self.active_engine.start()

    def push_message_callback(self, message):
        """Callback for ActiveEngine to push messages to UI."""
        import json
        if self._window:
            safe_msg = message.replace("'", "\\'").replace("\n", "\\n")
            
            # Detect JSON for TTS
            tts_text = message
            js_payload = f"'{safe_msg}'"
            
            try:
                data = json.loads(message)
                if "response" in data:
                    tts_text = data["response"]
                    # Re-serialize for Safe JS passing (as an Object)
                    # We pass the JSON string and let JS parse? Or pass Object literal?
                    # Let's pass the Object: receiveMessage({...})
                    js_payload = json.dumps(data, ensure_ascii=False)
            except json.JSONDecodeError:
                pass # Treat as raw text
            
            # Speak it
            out_path = self.generate_tts_audio(tts_text)
            
            # Single call to frontend
            audio_arg = f"'{out_path}'" if out_path else "null"
            # If js_payload is an object string (from json.dumps), it works directly as arg
            self._window.evaluate_js(f"receiveMessage({js_payload}, {audio_arg})")

    # --- Session Restore & Debugging (Phase 35) ---
    def restore_history(self):
        """API: Restore session history."""
        print(f"[Api] restore_history called.")
        if hasattr(self, 'history_manager') and self.history_manager:
            history = self.history_manager.get_session_history()
            print(f"[Api] Returning {len(history)} messages for restore.")
            return history
        print("[Api] History manager not initialized.")
        return []

    def debug_log(self, message: str):
        """Exposed for frontend logging via pywebview."""
        print(f"[CLIENT LOG] {message}")
        return {"status": "ok"}

# --- Background Task for Auto-Titling ---
def start_background_title_fixer(api_instance):
    """起動後に裏でこっそりタイトルを直すお掃除タスク (直近の話題で上書き版)"""
    import time
    def _run():
        import time
        time.sleep(5) # 起動待ち (少し待ってから開始)
        
        if not api_instance: return
        print("[TitleFixer] Starting background title generation (Latest Topic)...")
        
        # main.py runs in same process
        from src import core_instance
        db = core_instance.get_db()
        if not db: return

        # 修正対象: "インポートされた...", "[Situation]...", "無題の会話", "New Session", "すでに使っている", "AI:"
        # 取得
        sessions = db.get_sessions(limit=100) # 最近の100件をチェック
        
        target_prefixes = [
            "インポートされた", 
            "[Situation]", 
            "無題の会話", 
            "New Session", 
            "すでに使っている",
            "AI:", # AI発言がそのままタイトルになったものも修正
        ]
        
        for sess in sessions:
            s_id = sess['id']
            title = sess['title']
            
            # 条件に一致するかチェック
            is_target = any(title.startswith(p) for p in target_prefixes)
            if not is_target:
                continue
                
            # メッセージ取得
            msgs = db.get_messages(s_id)
            if not msgs: continue
            
            # ★修正: 「最初」ではなく「最後」の会話を使う
            # 会話が長い場合は、直近の10件を取得
            recent_msgs = msgs[-10:] if len(msgs) > 10 else msgs
            
            context = ""
            for m in recent_msgs:
                role = m['role']
                content = m['content']
                if not content: continue
                
                # システムコマンド除外
                if content.strip().startswith('['): continue
                
                if role == 'user':
                    context += f"User: {content}\n"
                elif role == 'ai':
                    context += f"AI: {content}\n"
            
            if len(context) < 10: continue

            print(f"[TitleFixer] Regenerating title for session {s_id} using LAST conversations...")
            
            # AI要約実行
            # api_instance._ai_engine access
            if hasattr(api_instance, '_ai_engine') and api_instance._ai_engine:
                 new_title = api_instance._ai_engine.generate_title_summary(context)
                 
                 if new_title:
                     # 引用符などが残っていたら削除
                     new_title = new_title.replace('"', '').replace("'", "").strip()
                     print(f"[TitleFixer] Updated: '{title}' -> '{new_title}'")
                     db.update_session_title(s_id, new_title)
                
            # APIレート制限考慮 
            time.sleep(2)
        print("[TitleFixer] Finished.")

    # スレッド起動
    threading.Thread(target=_run, daemon=True).start()

def create_app():
    api = Api()
    
    # ★ Start Background Title Fixer
    start_background_title_fixer(api)
    
    initial_width = 500 
    initial_height = 500
    
    # Load Position from Config
    # default to None (centers window)
    x = api._config_manager.get('window_x', None)
    y = api._config_manager.get('window_y', None)
    
    window = webview.create_window(
        'SoulMate AI', 
        'dist/index.html',
        js_api=api,
        width=initial_width,
        height=initial_height,
        x=x,
        y=y,
        transparent=True,
        frameless=True,
        on_top=True,
        easy_drag=False
    )
    api.set_window(window)
    webview.start(debug=True)

if __name__ == '__main__':
    # 1. Initialize Database
    print("Initializing Database (soulmate.db)...")
    from src.services.db_manager import DatabaseManager
    
    db = DatabaseManager()
    db.init_db()
    
    # 2. Register to Core
    from src import core_instance
    core_instance.set_db(db)
    
    # 3. Migrate Legacy History (JSON -> DB)
    from src.services.migration_service import MigrationService
    migration = MigrationService(db)
    migration.migrate_json_to_db()
    
    # 3.4 Clean Internal Logs (Force Talk pollution)
    migration.clean_internal_logs()
    
    # 3.5 Fix Legacy Titles (Imported sessions with default titles)
    migration.fix_legacy_titles()

    # 4. Ensure session exists
    if not db.get_active_session():
        print("Creating initial session...")
        db.create_session("はじめまして")
        
    create_app()