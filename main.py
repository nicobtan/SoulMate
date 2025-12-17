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

        # 1. Base Prompt (Persona)
        base_prompt = ""
        if self._persona_manager:
            data = self._persona_manager.load_persona(persona_id)
            if data:
                base_prompt = data.get('system_prompt', '')
            else:
                base_prompt = "You are a helpful AI."

        # 2. User Profile Context
        user_context = ""
        if self.user_manager:
            user_context = self.user_manager.get_profile_context()

        # 3. Topic Guidance
        topic_instruction = """
Guidance for conversation:
- Use the [User Profile] information to proactively suggest topics when the user is silent or asks for a topic.
- E.g., If the user likes 'Arknights', ask about their favorite character.
- E.g., If they are working on 'SoulMate project', ask about the specific progress.
"""

        # 4. JSON Mode Instruction (Required for frontend to work properly with suggestion chips)
        json_instruction = """
Response Format: JSON
You MUST respond in the following JSON format:
{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}
"""
        
        full_system_prompt = f"{base_prompt}\\n{user_context}\\n{topic_instruction}\\n\\n{json_instruction}"
        
        if self._ai_engine:
            self._ai_engine.set_system_prompt(full_system_prompt)
            self._ai_engine.configure(
                api_key=api_key, 
                model_name=model
            )
            
            # Pass API Key to VoiceService (for Gemini TTS)
            if self.voice_service and api_key:
                self.voice_service.set_api_key(api_key)

            print(f"[System] AI Configured: {model} with User Profile")

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

def create_app():
    api = Api()
    
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
    create_app()