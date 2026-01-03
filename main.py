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
from src.api.history_api import HistoryApiMixin
from src.services.bubble_service import BubbleService
from src.services.history_manager import HistoryManager

from src.services.user_manager import UserManager

from src.services.interest_manager import InterestManager
from src.services.topic_selector import TopicSelector

class Api(WindowApiMixin, SettingsApiMixin, ChatApiMixin, BubbleApi, UserApiMixin, HistoryApiMixin):
    def __init__(self):
        super().__init__() # Initialize BaseApiMixin attributes
        self.services = self # Mixin Pattern: API instance itself is the service container
        
        # 1. Core & Services Initialization
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self._persona_manager = PersonaManager()
        self._persona_manager = PersonaManager()
        self._memory_manager = MemoryManager()
        self.history_manager = HistoryManager()

        # Database Manager (SQLite)
        from src.services.db_manager import DatabaseManager
        self.db_manager = DatabaseManager()
        self.db_manager.init_db()
        
        # Register to Core Instance (for ChatApi access)
        from src import core_instance
        core_instance.set_db(self.db_manager)
        
        # User & Interest Manager
        self.user_manager = UserManager()
        self.user_manager = UserManager()
        self.interest_manager = InterestManager()
        self.topic_selector = TopicSelector()
        
        # Soul Bubble Service
        self.bubble_service = BubbleService(self)

        # Wire up Loggers for Observability
        # 1. Mind Log (AI Thought -> Frontend Mind Tab)
        self._ai_engine.set_mind_logger(self.log_to_mind)
        
        # 2. RAG Log (Memory Search -> Frontend RAG Tab)
        # Using lambda to route to log_to_debug with 'rag' type
        self._memory_manager.set_rag_logger(lambda msg: self.log_to_debug(msg, 'rag'))

        # --- Diary Generator (Phase 89) ---
        from src.services.diary_generator import DiaryGenerator
        self.diary_generator = DiaryGenerator(self)
        # Thread started in set_window()


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
        self.active_engine = ActiveEngine(self._ai_engine, self.push_message_callback, log_callback=self.log_to_debug)
        self.active_engine.configure(self._config_manager.get_all())
        
        # Connect VisionService Logging
        from src.services.vision_service import vision_service
        vision_service.set_log_callback(self.log_to_debug)
        
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
        # Test Bubble Timer (Validation)
        # Main Bubble Loop (Safe)
        def bubble_loop():
            import time
            time.sleep(5) # Wait for startup
            
            # Wait for JS Readiness
            while True:
                if self._window:
                    try:
                        # Check if function exists
                        is_ready = self._window.evaluate_js("typeof showSoulBubble === 'function'")
                        if is_ready:
                            print("[System] Frontend JS Ready.")
                            break
                    except Exception:
                        pass
                time.sleep(1)

            while True:
                if self._window:
                    try:
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
                    except Exception as e:
                         print(f"[System] Bubble Loop Error: {e}")
                    
                time.sleep(5) # Check frequently (Service handles 5min throttling)
        
        threading.Thread(target=bubble_loop, daemon=True).start()

    def _configure_ai(self, settings):
        """Override to include User Profile Context"""
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-3-flash-preview')

        # Safety: Force correct model name if old config exists (Generic 3.0 -> 3)
        if 'gemini-3.0' in model:
            model = model.replace('gemini-3.0', 'gemini-3')

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

[CRITICAL: NO LECTURES]
- **No Unsolicited Trivia**: Do NOT explain terms, history, or trivia unless explicitly asked.
- **No Teaching Mode**: You are a partner, not a teacher. Do not say "Did you know?" or "By the way...".
- **Reaction First**: Prioritize emotional reaction over information.

[LENGTH: SHORT & SWEET]
- **Keep it Short**: 1-2 sentences max per response.
- **No Walls of Text**: User is working. Do not interrupt with long text.

[FINAL REMINDER]
Your partner's name is "{user_name}". Use it naturally in conversation.
Do NOT use placeholders like "〇〇さん".
Do not preach about health before 02:00 AM.

[CRITICAL INSTRUCTION: CONTEXT CONTINUITY]
1. If the user's input is short or ambiguous (e.g., "Tell me more", "Why?", "Details?", "Really?"):
   - You MUST strictly refer to the IMMEDIATE CONVERSATION HISTORY (Short Term Memory).
   - Elaborate on the TOPIC DISCUSSED IN THE PREVIOUS TURN.
   - DO NOT switch topics or explain your underlying AI architecture (e.g., Gemini, LLM specs) unless explicitly asked.
Priority of Reference: [Highest] Immediate User/AI Dialogue History [Medium] Current Scene/Persona Context [Lowest] General Knowledge/System Specs
"""

        
        if self._ai_engine:
            self._ai_engine.set_system_prompt(deep_context_prompt)
            self._ai_engine.configure(
                api_key=api_key, 
                reasoning_model=model
            )
            
            # Pass API Key to VoiceService (for Gemini TTS)
            if self.voice_service and api_key:
                self.voice_service.set_api_key(api_key)

            print(f"[System] AI Configured: {model} with Deep Context ({user_name})")

    def set_window(self, window):
        self._window = window
        # Hook loaded event for startup settings (Background restore)
        self._window.events.loaded += self.on_window_loaded
        
        self.active_engine.start()
        # Start Diary Check (Delayed to ensure UI is ready)
        threading.Thread(target=self.diary_generator.check_and_generate_diary, daemon=True).start()

    def on_window_loaded(self):
        """Called when the main window DOM is ready."""
        print("[System] Main Window Loaded. Applying startup settings...")
        
        # 1. Restore Background Image (via Base64 injection)
        self.apply_background_image()
        
        # 2. Restore Window Position (Explicitly move with delay to bypass renderer init)
        x = self._config_manager.get('window_x', None)
        y = self._config_manager.get('window_y', None)
        
        if x is not None and y is not None:
            def delayed_move():
                import time
                time.sleep(1.0) # Wait for WebView to fully initialize
                try:
                    current_x, current_y = self._window.x, self._window.y
                    print(f"[System] Delayed Move: Current({current_x}, {current_y}) -> Target({x}, {y})")
                    if abs(current_x - int(x)) > 10 or abs(current_y - int(y)) > 10:
                        self._window.move(int(x), int(y))
                        print("[System] Window Position Corrected.")
                    else:
                        print("[System] Window Position already correct.")
                except Exception as e:
                    print(f"[System] Failed to move window: {e}")
            
            threading.Thread(target=delayed_move, daemon=True).start()

    def push_message_callback(self, message):
        """Callback for ActiveEngine to push messages to UI."""
        import json
        if self._window:
            safe_msg = message.replace("'", "\\'").replace("\n", "\\n")
            
            # Detect JSON
            tts_text = message
            js_payload = f"'{safe_msg}'"
            
            is_expression_only = False

            try:
                data = json.loads(message)
                
                # Check for control-only messages
                if "type" in data and data["type"] == "expression":
                    # Just trigger expression
                    expr_name = data.get("name", "neutral")
                    self._window.evaluate_js(f"if(window.setExpression) window.setExpression('{expr_name}')")
                    return # Stop here, no TTS
                    
                if "response" in data:
                    tts_text = data["response"]
                    js_payload = json.dumps(data, ensure_ascii=False)
                elif "text" in data:
                    tts_text = data["text"]
                    js_payload = json.dumps(data, ensure_ascii=False)
            except json.JSONDecodeError:
                pass # Treat as raw text
            
            # Speak it
            out_path = self.generate_tts_audio(tts_text)
            
            # Single call to frontend
            audio_arg = f"'{out_path}'" if out_path else "null"
            self._window.evaluate_js(f"receiveMessage({js_payload}, {audio_arg})")

    # --- Session Restore & Debugging (Phase 35) ---
    def restore_history(self):
        """API: Restore session history from DB (Desktop Logic)."""
        # ★ User Request: Log start of restore
        self.log_to_debug("🚀 [History] Restoring active session...", 'info')
        
        from src import core_instance
        db = core_instance.get_db()
        
        if not db:
            self.log_to_debug("❌ [History] DB not available/initialized.", 'error')
            return []

        # 1. Get Active Session
        active_session = db.get_active_session()
        
        # If no active session, try to get last valid one
        if not active_session:
             last = db.get_last_session()
             if last:
                 db.set_session_active(last['id'])
                 active_session = last
                 self.log_to_debug(f"⚠️ [History] No active session found. Resumed last session: '{last.get('title')}'", 'warn')
        
        if not active_session:
            self.log_to_debug("💨 [History] No sessions found to restore.", 'info')
            return []

        # 2. Get Messages
        try:
            messages = db.get_messages(active_session['id'])
            
            # 3. Format for Frontend
            # Frontend expects: { role, content } (mapped from ChatManager logic)
            history_data = []
            for m in messages:
                if not m['content']: continue
                
                history_data.append({
                    "role": m['role'],
                    "content": m['content']
                })
            
            # ★ User Request: Log completion
            self.log_to_debug(f"✅ [History] Restored {len(history_data)} messages from '{active_session.get('title')}'.", 'info')
            return history_data

        except Exception as e:
            self.log_to_debug(f"❌ [History] Restore Failed: {e}", 'error')
            return []

    def debug_log(self, message: str):
        """Exposed for frontend logging via pywebview."""
        print(f"[CLIENT LOG] {message}")
        return {"status": "ok"}

# --- Background Task for Auto-Titling ---
def start_background_title_fixer(api_instance):
    """起動後に裏でこっそり会話タイトルを修正するタスク (直近の話題に基づいてリネーム)"""
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
    
    initial_width = 450 
    initial_height = 700
    
    # Load Position from Config
    # default to None (centers window)
    raw_x = api._config_manager.get('window_x', None)
    raw_y = api._config_manager.get('window_y', None)
    
    x = int(raw_x) if raw_x is not None else None
    y = int(raw_y) if raw_y is not None else None
    
    print(f"[Main] Initial Window Position: x={x}, y={y}")
    
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
    
    # ★ Setting API Instance for Auth Logging
    from src.services.google_auth_manager import GoogleAuthManager
    GoogleAuthManager().set_api_instance(api)

    # ★ Inner Voice (Mind Logs) Wiring
    # Set Mind Logger if Engine exists
    if hasattr(api, '_ai_engine') and api._ai_engine:
        api._ai_engine.set_mind_logger(api.log_to_mind)

    # ★ Cloud MindVault Sync (Phase 91)
    try:
        def sync_mind_vault_flow():
            import time
            time.sleep(3) # Wait for network stabilization
            
            # 1. Google Doc -> Local MD
            from src.services.docs_sync import DocsSyncService
            syncer = DocsSyncService(api) # Pass API for AI Engine access
            local_md = os.path.join(os.getcwd(), "settings", "MindVault.md")
            syncer.fetch_and_sync(doc_title="MindVault", local_path=local_md)
            
            # 2. Local MD -> DB
            from src.services.mind_loader import MindLoader
            loader = MindLoader(api)
            loader.sync_mind_vault(local_md)
            
        threading.Thread(target=sync_mind_vault_flow, daemon=True).start()
        
    except Exception as e:
        print(f"[Main] CloudSync Init Error: {e}")

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

    # 4. Ensure session exists (Resume Logic)
    active_session = db.get_active_session()
    
    if active_session:
        print(f"Resuming active session: ID {active_session['id']} ({active_session['title']})")
    else:
        # アクティブがない場合、最新のセッションを探して復帰させる
        last_session = db.get_last_session()
        if last_session:
            print(f"Resuming last session: ID {last_session['id']} ({last_session['title']})")
            db.set_session_active(last_session['id'])
        else:
            # 履歴が全くない場合のみ新規作成
            print("Creating initial session...")
            db.create_session("はじめまして")
        
    # --- JSONL -> SQL Synchronize ---
    print("Synchronizing JSONL logs to active session...")
    migration.sync_jsonl_to_db()

    create_app()