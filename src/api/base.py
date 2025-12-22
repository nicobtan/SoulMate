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
            import json
            # JSON Dump ensures safe string escaping for JS
            safe_msg = json.dumps(str(msg))
            safe_type = json.dumps(type)
            # safe_msg includes quotes, so we don't need to add them in f-string
            self._window.evaluate_js(f"logToDebug({safe_msg}, {safe_type})")

    def log_to_mind(self, msg):
        """Log AI thought process to the Mind tab."""
        print(f"[MIND] {msg}")
        if self._window:
            import json
            safe_msg = json.dumps(str(msg))
            self._window.evaluate_js(f"logToMind({safe_msg})")
