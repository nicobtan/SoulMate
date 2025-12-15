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

class Api(WindowApiMixin, SettingsApiMixin, ChatApiMixin):
    def __init__(self):
        super().__init__() # Initialize BaseApiMixin attributes
        
        # 1. Core & Services Initialization
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self._persona_manager = PersonaManager()
        self._memory_manager = MemoryManager()
        
        # TTS Engine
        cred_path = os.path.join(base_dir, 'google-credentials.json')
        try:
            # Note: TTSEngine in src/services might need adjustment if it doesn't default correctly?
            # Step 2138 used key_path="google-credentials.json". 
            # We assume google-credentials.json is in ROOT.
            # TTSEngine logic uses os.environ if key_path passed.
            self.tts_engine = TTSEngine(key_path="google-credentials.json")
            print("[System] TTS Engine initialized.")
        except Exception as e:
            print(f"[System] TTS Init Failed: {e}")
            self.tts_engine = None

        # Active Engine
        self.active_engine = ActiveEngine(self._ai_engine, self.push_message_callback)
        self.active_engine.configure(self._config_manager.get_all())
        
        # Apply Initial Config
        settings = self._config_manager.get_all()
        # _configure_ai is defined in SettingsApiMixin
        self._configure_ai(settings)

        # Calendar Manager & Auto-Auth
        self._calendar_manager = CalendarManager()
        def auto_auth():
            self._calendar_manager.authenticate() 
            print(f"[System] Auto-Auth Result: {self._calendar_manager.is_authenticated}")
        threading.Thread(target=auto_auth, daemon=True).start()

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
            out_path = None
            if self.tts_engine:
                 voice = self._config_manager.get('voice_type', 'ja-JP-Neural2-B')
                 # Helper to clean text
                 import re
                 # Remove simple URLs
                 clean_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', tts_text)
                 
                 out_path = self.tts_engine.generate_voice(
                     clean_text, 
                     output_dir=os.path.join(base_dir, 'dist/audio'), 
                     voice_name=voice
                 )
            
            # Single call to frontend
            audio_arg = f"'{out_path}'" if out_path else "null"
            # If js_payload is an object string (from json.dumps), it works directly as arg
            self._window.evaluate_js(f"receiveMessage({js_payload}, {audio_arg})")

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
        on_top=True
    )
    api.set_window(window)
    webview.start(debug=True)

if __name__ == '__main__':
    create_app()