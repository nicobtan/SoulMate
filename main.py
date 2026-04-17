import sys
import os
import webview
import threading

# Add root dir to sys.path explicitly to allow 'src' imports
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Load Environment Variables Early
from dotenv import load_dotenv
load_dotenv()

# Imports from new structure
from src.core.config_manager import ConfigManager
from src.services.core.ai_engine import AIEngine
from src.services.core.persona_manager import PersonaManager
from src.services.memory.memory_service import MemoryService # Import
from src.services.memory.memory_manager import MemoryManager
from src.services.voice.tts_engine import TTSEngine
from src.services.core.active_engine import ActiveEngine
from src.services.external.calendar_manager import CalendarManager
from src.services.voice.soulmate_ears import SoulMateEars # Import Ears

# Imports from API Mixins
from src.api.window_api import WindowApiMixin
from src.api.settings_api import SettingsApiMixin
from src.api.chat_api import ChatApiMixin
from src.api.bubble_api import BubbleApi
from src.api.user_api import UserApiMixin
from src.api.history_api import HistoryApiMixin
from src.api.voice_api import VoiceApiMixin
from src.api.character_api import CharacterApiMixin
from src.api.vision_api import VisionApiMixin
from src.api.quick_message_api import QuickMessageApiMixin
from src.services.content.bubble_service import BubbleService
from src.services.core.character_service import CharacterService
from src.services.memory.history_manager import HistoryManager

from src.services.core.user_manager import UserManager
from src.services.content.interest_manager import InterestManager
from src.services.content.topic_selector import TopicSelector

class Api(WindowApiMixin, SettingsApiMixin, ChatApiMixin, BubbleApi, UserApiMixin, HistoryApiMixin, VoiceApiMixin, CharacterApiMixin, VisionApiMixin, QuickMessageApiMixin):
    def __init__(self):
        super().__init__() # Initialize BaseApiMixin attributes
        self.services = self # Mixin Pattern: API instance itself is the service container
        
        # 0. Lifecycle Flags
        self.is_cleaning_up = False
        self._window = None
        self._controller_window = None
        self._live2d_window = None
        self._live2d_visible = False
        
        # 1. Core & Services Initialization
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        
        self._persona_manager = PersonaManager()
        self._memory_manager = MemoryManager()
        self.history_manager = HistoryManager()
        
        # ★ Memory Service (Learned Facts)
        self.memory_service = MemoryService()
        self._ai_engine.set_memory_service(self.memory_service)

        # Database Manager (SQLite)
        from src.services.memory.db_manager import DatabaseManager
        self.db_manager = DatabaseManager()
        self.db_manager.init_db()
        
        # Register to Core Instance (for ChatApi access)
        from src import core_instance
        core_instance.set_db(self.db_manager)
        
        # User & Interest Manager
        self.user_manager = UserManager()
        self.interest_manager = InterestManager()
        self.topic_selector = TopicSelector()
        
        # Character Service
        self.character_service = CharacterService(self)
        
        # Soul Bubble Service
        self.bubble_service = BubbleService(self)

        # Wire up Loggers for Observability
        # 1. Mind Log (AI Thought -> Frontend Mind Tab)
        self._ai_engine.set_mind_logger(self.log_to_mind)
        
        # 2. RAG Log (Memory Search -> Frontend RAG Tab)
        # Using lambda to route to log_to_debug with 'rag' type
        self._memory_manager.set_rag_logger(lambda msg: self.log_to_debug(msg, 'rag'))

        # --- Diary Generator (Phase 89) ---
        from src.services.content.diary_generator import DiaryGenerator
        self.diary_generator = DiaryGenerator(self)
        
        # TTS Engine
        try:
            key_path = os.path.join(os.getcwd(), "settings", "google-credentials.json")
            self._tts_engine = TTSEngine(key_path=key_path)
            print("[System] TTS Engine initialized.")
        except Exception as e:
            print(f"[System] TTS Init Failed: {e}")
            self._tts_engine = None

        # VOICEVOX Service
        try:
            from src.services.voice.voice_service import VoiceService
            self._voice_service = VoiceService()
            print("[System] VoiceService initialized.")
        except Exception as e:
            print(f"[System] VoiceService Init Failed: {e}")
            self._voice_service = None

        # SoulMateEars (Hearing)
        # SoulMateEars (Hearing)
        try:
             # Default CPU/CUDA is handled by SoulMateEars internal logic or default arg
             # self._soulmate_ears = SoulMateEars() 
             # print("[System] SoulMateEars initialized.")
             print("[System] SoulMateEars DISABLED for debugging.")
             self._soulmate_ears = None
        except Exception as e:
             print(f"[System] SoulMateEars Init Failed: {e}")
             self._soulmate_ears = None
 
        # Active Engine
        self._active_engine = ActiveEngine(self._ai_engine, self.push_message_callback, log_callback=self.log_to_debug)
        self._active_engine.set_bubble_service(self.bubble_service) # Inject Bubble Service
        if self._soulmate_ears:
            self._active_engine.set_ears(self._soulmate_ears) # Inject Ears
        self._active_engine.configure(self._config_manager.get_all())
        
        # Connect VisionService Logging
        from src.services.vision.vision_service import vision_service
        vision_service.set_log_callback(self.log_to_debug)

        # Connect WindowTargetManager Logging & UI Updates
        from src.services.vision.window_target_manager import window_target_manager
        window_target_manager.set_log_callback(lambda msg, type='vision': self.log_to_debug(msg, type))
        
        def update_vision_target_ui(app_name, is_locked):
            if self._window:
                js = f"updateVisionTarget('{app_name}', {'true' if is_locked else 'false'})"
                self._window.evaluate_js(js)
                
        window_target_manager.set_target_callback(update_vision_target_ui)

        
        # Apply Initial Config
        settings = self._config_manager.get_all()
        self._configure_ai(settings)
        # Restore last used character (Live2D Model + Persona + Voice)
        if hasattr(self, 'character_service'):
            last_char_id = settings.get('current_character_id')
            if last_char_id and last_char_id != 'default':
                print(f"[System] Restoring last character: {last_char_id}")
                self.character_service.switch_character(last_char_id)

        # Apply Voice Hotkey
        if hasattr(self, 'configure_voice_hotkey'):
             self.configure_voice_hotkey(settings)

        # Calendar Manager & Auto-Auth
        self._calendar_manager = CalendarManager()
        # Note: auto_auth moved to start_services()
        

        # Note: bubble_loop moved to start_services()

        # Phase 130: OS Control Services (Singleton Usage)
        try:
             # Use the singleton instance explicitly to avoid double-init/Tkinter conflicts
             from src.services.control.soul_operator import soul_operator
             from src.services.control.experience_logger import ExperienceLogger
             self._soul_operator = soul_operator
             self._soul_operator.set_window_provider(self.get_window_pos) # Inject Position Provider
             self._soul_operator.set_services(self.character_service, self.user_manager)
             self._experience_logger = ExperienceLogger()
             print("[System] SoulOperator (OS Control) Initialized.")
        except Exception as e:
             msg = f"[System] SoulOperator Init Failed: {e}"
             print(msg)
             self.log_to_debug(msg, 'error') # Show in UI
             self._soul_operator = None
             self._soul_operator_init_error = str(e) # Store for ChatApi
             self._experience_logger = None


    def cleanup(self):
        """Releases all resources on shutdown."""
        if getattr(self, 'is_cleaning_up', False): return
        self.is_cleaning_up = True
        print("[System] Shutting down services...")
        
        # Stop Listeners
        if hasattr(self, '_active_engine') and self._active_engine:
            self._active_engine.stop()
            
        # Stop Ears
        if hasattr(self, '_soulmate_ears') and self._soulmate_ears:
            self._soulmate_ears.close()

        # Stop TTS
        if hasattr(self, '_tts_engine') and self._tts_engine:
            pass
            
        print("[System] Cleanup complete.")

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

        # ★ Learned Facts Injection
        learned_facts_str = "(No learned facts yet)"
        if self.memory_service:
            learned_facts_str = self.memory_service.get_learned_facts_text()

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
            if self._voice_service and api_key:
                self._voice_service.set_api_key(api_key)

            print(f"[System] AI Configured: {model} with Deep Context ({user_name})")

    def set_window(self, window):
        self._window = window
        # Hook loaded event for startup settings (Background restore)
        self._window.events.loaded += self.on_window_loaded
        
        # Note: active_engine.start() and diary check moved to start_services()

    def start_agent(self):
        """Called from Controller GUI"""
        print("[System] Controller: Start Agent")
        
        if hasattr(self, '_active_engine') and self._active_engine:
            self._active_engine.set_stealth_mode(True)
            self._active_engine.start()
            
        if self._controller_window:
            self._controller_window.evaluate_js("updateStatus('RUNNING (Stealth)')")
            self._controller_window.evaluate_js("addLog('System: Agent loop started in background.')")

    def stop_agent(self):
        """Called from Controller GUI"""
        print("[System] Controller: Stop Agent")
        
        if hasattr(self, '_active_engine') and self._active_engine:
            self._active_engine.stop()
            
        if self._controller_window:
            self._controller_window.evaluate_js("updateStatus('STOPPED')")
            self._controller_window.evaluate_js("addLog('System: Agent loop stopped.')")

    def toggle_live2d(self):
        """Called from Controller GUI"""
        if self._live2d_window:
            if getattr(self, '_live2d_visible', False):
                self._live2d_window.hide()
                self._live2d_visible = False
                print("[System] Live2D Hidden")
                if self._controller_window:
                    self._controller_window.evaluate_js("addLog('System: Live2D Window Hidden')")
            else:
                self._live2d_window.show()
                self._live2d_visible = True
                print("[System] Live2D Shown")
                if self._controller_window:
                    self._controller_window.evaluate_js("addLog('System: Live2D Shown (Stealth Mode Disabled)')")
                
                # Turn OFF stealth mode
                if hasattr(self, '_active_engine') and self._active_engine:
                    self._active_engine.set_stealth_mode(False)
        else:
            print("[System] Creating Live2D Window")
            # Create Window
            initial_width = 450 
            initial_height = 700
            
            raw_x = self._config_manager.get('window_x', None)
            raw_y = self._config_manager.get('window_y', None)
            x = int(raw_x) if raw_x is not None else None
            y = int(raw_y) if raw_y is not None else None
            
            self._live2d_window = webview.create_window(
                'SoulMate AI', 
                'dist/index.html',
                js_api=self,
                width=initial_width,
                height=initial_height,
                x=x,
                y=y,
                transparent=True,
                frameless=True,
                on_top=self._config_manager.get('always_on_top', True),
                easy_drag=False
            )
            
            self._window = self._live2d_window
            self._live2d_visible = True
            
            self._live2d_window.events.loaded += self.on_window_loaded
            
            if self._controller_window:
                 self._controller_window.evaluate_js("addLog('System: Live2D Window Created')")
                 
            # Turn OFF stealth mode
            if hasattr(self, '_active_engine') and self._active_engine:
                self._active_engine.set_stealth_mode(False)

    def start_services(self):
        """Initializes background services after UI is ready (Event Driven)."""
        print("[System] Starting Background Services...")
        self.log_to_debug("[System] 🔄 Starting Background Services...", 'sys')
        
        # 1. Active Engine
        if hasattr(self, '_active_engine') and self._active_engine:
            self._active_engine.start()
            print("[System] ActiveEngine Started.")
            self.log_to_debug("[System] ✅ ActiveEngine Started.", 'sys')

        # 2. Bubble Service (Loop)
        def bubble_loop():
            import time
            time.sleep(2) # Short wait for safety
            
            # Double check JS Readiness
            while True:
                if self._window:
                    try:
                        if self._window.evaluate_js("typeof showSoulBubble === 'function'"):
                            break
                    except: pass
                time.sleep(1)
            
            print("[System] Bubble Loop Started.")
            self.log_to_debug("[System] ✅ Bubble Service Loop Started.", 'sys')

            while True:
                if self._window:
                    try:
                        # Check safe to access window
                        # Use refill_bubbles() which respects MAX limits and Time Intervals
                        packets = self.bubble_service.refill_bubbles()
                        if packets:
                            for packet in packets:
                                b_type = packet.get('type', 'normal')
                                # Ensure safe quoting
                                safe_text = packet['text'].replace("'", "\\'")
                                safe_cat = packet['category'].replace("'", "\\'")
                                
                                js = f"showSoulBubble('{safe_cat}', '{safe_text}', '{packet['action_id']}', '{b_type}')"
                                self._window.evaluate_js(js)
                                print(f"[System] Bubble Injected: {packet['text']} ({b_type})")
                    except Exception as e:
                         print(f"[System] Bubble Loop Error: {e}")
                    
                time.sleep(5) 
        
        threading.Thread(target=bubble_loop, daemon=True).start()

        # 3. Calendar Auth
        def auto_auth():
            if self._calendar_manager:
                self._calendar_manager.authenticate() 
                print(f"[System] Auto-Auth Result: {self._calendar_manager.is_authenticated}")
                if self._calendar_manager.is_authenticated:
                     self.log_to_debug("[System] ✅ Calendar Authenticated.", 'sys')
        threading.Thread(target=auto_auth, daemon=True).start()

        # 4. Diary Generator
        if self.diary_generator:
            threading.Thread(target=self.diary_generator.check_and_generate_diary, daemon=True).start()

        # 5. Title Fixer
        start_background_title_fixer(self)

        # 6. Cloud MindVault Sync
        def sync_mind_vault_flow():
            import time
            time.sleep(3) 
            from src.services.external.docs_sync import DocsSyncService
            try:
                syncer = DocsSyncService(self)
                local_md = os.path.join(os.getcwd(), "settings", "MindVault.md")
                syncer.fetch_and_sync(doc_title="MindVault", local_path=local_md)
                
                from src.services.memory.mind_loader import MindLoader
                loader = MindLoader(self)
                loader.sync_mind_vault(local_md)
                self.log_to_debug("[System] ✅ MindVault Synced.", 'sys')
            except Exception as e:
                print(f"[System] CloudSync Error: {e}")

        threading.Thread(target=sync_mind_vault_flow, daemon=True).start()

        print("[System] 🚀 All Systems Operational. SoulMate is Ready.")
        self.log_to_debug("[System] 🚀 All Systems Operational. SoulMate is Ready.", 'sys')

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
            
            # ★ Start Services (Event Driven)
            self.start_services()

    def _handle_voice_input_payload(self, data):
        """Handle voice input from ActiveEngine loop (simulate user message)"""
        text = data.get("text", "")
        if not text: return
        
        safe_text = text.replace("'", "\\'").replace("\n", " ")
        if self._window:
            # 1. Insert text into input box
            self._window.evaluate_js(f"if(window.insertVoiceText) window.insertVoiceText('{safe_text}')")
            # 2. Click Send Button
            self._window.evaluate_js("document.getElementById('chat-send-btn')?.click()")

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
                
                # Check for stealth_log
                if "type" in data and data["type"] == "stealth_log":
                    if self._controller_window:
                        safe_log = data["text"].replace("'", "\\'")
                        self._controller_window.evaluate_js(f"addLog('{safe_log}')")
                    return
                
                # Check for voice_input (New)
                if "type" in data and data["type"] == "voice_input":
                     self._handle_voice_input_payload(data)
                     return
                
                # Check for control-only messages
                if "type" in data and data["type"] == "expression":
                    # Just trigger expression
                    expr_name = data.get("name", "neutral")
                    self._window.evaluate_js(f"if(window.setExpression) window.setExpression('{expr_name}')")
                    return # Stop here, no TTS

                if "type" in data and data["type"] == "bubble":
                    # Trigger Soul Bubble
                    cat = data.get("category", "topics")
                    txt = data.get("text", "")
                    aid = data.get("action_id", "")
                    b_type = data.get("type_ui", "discovery") # 'discovery' makes it purple
                    
                    # Call showSoulBubble directly
                    js = f"showSoulBubble('{cat}', '{txt}', '{aid}', '{b_type}')"
                    self._window.evaluate_js(js)
                    return # Stop here
                    
                if "response" in data:
                    tts_text = data["response"]
                    js_payload = json.dumps(data, ensure_ascii=False)
                elif "text" in data:
                    tts_text = data["text"]
                    js_payload = json.dumps(data, ensure_ascii=False)
            except json.JSONDecodeError:
                pass # Treat as raw text
            
            # ★ Save to History (Proactive/Bubble messages)
            if tts_text:
                # 1. JSONL Backup (chat_history.jsonl)
                if hasattr(self, 'history_manager') and self.history_manager:
                    self.history_manager.add_message("ai", tts_text)
                
                # 2. SQLite Database
                try:
                    from src import core_instance
                    db = core_instance.get_db()
                    if db:
                        active = db.get_active_session()
                        if active:
                            session_id = active['id']
                            meta = data if isinstance(data, dict) else None
                            db.add_message(session_id, "ai", tts_text, meta=meta)
                except Exception as e:
                    self.log_to_debug(f"Proactive DB Save Error: {e}", 'error')

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
    
    # api = Api() # Duplicate removed
    
    # Debug: Check if get_settings is available
    print("[Main] Inspecting API methods...")
    methods = [m for m in dir(api) if not m.startswith('_')]
    if 'get_settings' in methods:
        print("[Main] ✅ get_settings FOUND in API class.")
    else:
        print("[Main] ❌ get_settings NOT FOUND in API class!")
        # Force check base classes
        print(f"[Main] API MRO: {Api.mro()}")

    # Title Fixer moved to api.start_services()
    
    print(f"[Main] Starting Controller UI...")
    
    controller_window = webview.create_window(
        'SoulMate Controller',
        'dist/controller.html',
        js_api=api,
        width=300,
        height=180,
        frameless=False,
        easy_drag=True
    )
    
    api._controller_window = controller_window
    
    # ★ Shutdown Hook
    def on_controller_closed():
        print("[Main] Controller window closed. Triggering cleanup...")
        try:
            api.save_window_position()
        except: pass
        api.cleanup()
        os._exit(0) # Force kill to prevent zombies

    controller_window.events.closed += on_controller_closed
    
    # ★ Setting API Instance for Auth Logging
    from src.services.external.google_auth_manager import GoogleAuthManager
    GoogleAuthManager().set_api_instance(api)

    # ★ Inner Voice (Mind Logs) Wiring
    # Set Mind Logger if Engine exists
    if hasattr(api, '_ai_engine') and api._ai_engine:
        api._ai_engine.set_mind_logger(api.log_to_mind)

    # ★ Cloud MindVault Sync moved to api.start_services()

    webview.start(debug=True)
    
    # Fallback exit if window close event missed
    print("[Main] Webview loop ended. Exiting...")
    os._exit(0)

if __name__ == '__main__':
    # 1. Initialize Database
    print("Initializing Database (soulmate.db)...")
    from src.services.memory.db_manager import DatabaseManager
    
    db = DatabaseManager()
    db.init_db()
    
    # 2. Register to Core
    from src import core_instance
    core_instance.set_db(db)
    
    # 3. Migrate Legacy History (JSON -> DB)
    from src.services.memory.migration_service import MigrationService
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