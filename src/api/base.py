import sys

class BaseApiMixin:
    """Base mixin to define expected attributes and common utilities."""
    
    def __init__(self):
        # Type hints for properties initialized in Main
        self._window = None
        self.config_manager = None
        self.ai_engine = None
        self.calendar_manager = None
        self.memory_manager = None
        self.tts_engine = None
        self.active_engine = None
        self.persona_manager = None

    def log_to_debug(self, msg, type='info'):
        """Log message to the frontend debug console."""
        print(f"[{type.upper()}] {msg}")
        if self._window:
            safe_msg = msg.replace("'", "\\'").replace("\n", "\\n")
            self._window.evaluate_js(f"logToDebug('{safe_msg}', '{type}')")
