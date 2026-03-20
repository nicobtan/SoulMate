
import win32gui
import time
import logging
from typing import Optional, Dict, Any

# Lazy imports to avoid circular dependencies or heavy load at startup
# form src.services.games.aoe2.commentary_engine import AoE2CommentaryEngine
# from src.services.games.aoe2.db_manager import AoE2DatabaseManager

logger = logging.getLogger(__name__)

class ContextManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.active_modules: Dict[str, Any] = {}
        self.current_context: Optional[str] = None
        self.last_context_change = time.time()
        self.cooldown_sec = 5.0
        
        # Mapping: Keyword -> ModuleKey
        self.context_rules = {
            "Age of Empires": "aoe2" 
            # Future: "Valorant": "valorant", "VS Code": "coding"
        }
        
        self.log_callback = None
        self._initialized = True

    def set_log_callback(self, callback):
        self.log_callback = callback
    
    def _log(self, message, type='sys'):
        logger.info(message)
        if self.log_callback:
            self.log_callback(message, type=type)

    def update(self):
        """
        Called periodically by ActiveEngine.
        Checks active window and manages module lifecycle.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return

        # Identify Context
        detected_context = None
        for keyword, context_key in self.context_rules.items():
            if keyword in title:
                detected_context = context_key
                break
        
        # Context Transition Logic
        if detected_context != self.current_context:
            now = time.time()
            if now - self.last_context_change < self.cooldown_sec:
                return # Debounce
            
            self._handle_transition(self.current_context, detected_context)
            self.current_context = detected_context
            self.last_context_change = now

    def _handle_transition(self, old_context, new_context):
        """Unload old, Load new."""
        
        # Unload Old
        if old_context == "aoe2":
            self._deactivate_aoe2()
            
        # Load New
        if new_context == "aoe2":
            self._activate_aoe2()

    def _activate_aoe2(self):
        try:
            self._log("🏰 [Context] Detected 'Age of Empires'! Initializing Battle Consultant Mode...", type="sys")
            
            from src.services.games.aoe2.db_manager import AoE2DatabaseManager
            from src.services.games.aoe2.commentary_engine import AoE2CommentaryEngine
            
            db_mgr = AoE2DatabaseManager()
            engine = AoE2CommentaryEngine(db_mgr)
            
            self.active_modules["aoe2"] = engine
            self._log("⚔️ [Context] AoE2 Module Activated. game_aoe2.db loaded.", type="sys")
            
        else:
            self._log("⚔️ [Context] AoE2 Module Activated. game_aoe2.db loaded.", type="sys")
            self._trigger_voice("AoE2実況モード、起動しました。戦況を見守りますね！")

    def set_message_callback(self, callback):
        self.message_callback = callback

    def _trigger_voice(self, text, emotion="happy"):
        if hasattr(self, 'message_callback') and self.message_callback:
            import json
            payload = {
                "text": text,
                "emotion": emotion,
                "suggestions": ["頑張る！", "ありがとう"],
                "type": "proactive"
            }
            self.message_callback(json.dumps(payload, ensure_ascii=False))

    def _deactivate_aoe2(self):
        if "aoe2" in self.active_modules:
            del self.active_modules["aoe2"]
            self._log("💤 [Context] AoE2 Module Deactivated (Memory Released).", type="sys")

    def get_active_engine(self):
        """Returns the currently active game engine instance, or None."""
        if self.current_context and self.current_context in self.active_modules:
            return self.active_modules[self.current_context]
        return None
