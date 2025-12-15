import sys

class BaseApiMixin:
    """Base mixin to define expected attributes and common utilities."""
    
    def __init__(self):
        # Type hints for properties initialized in Main
        self._window = None
        self._config_manager = None
        self._ai_engine = None
        self._calendar_manager = None
        self._memory_manager = None
        self.tts_engine = None
        self.active_engine = None
        self._persona_manager = None

    def log_to_debug(self, msg, type='info'):
        """Log message to the frontend debug console."""
        print(f"[{type.upper()}] {msg}")
        if self._window:
            safe_msg = msg.replace("'", "\\'").replace("\n", "\\n")
            self._window.evaluate_js(f"logToDebug('{safe_msg}', '{type}')")
