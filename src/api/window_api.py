import sys
from .base import BaseApiMixin

# Global reference to prevent recursion in pywebview serialization
SETTINGS_WINDOW_REF = {"window": None}

class WindowApiMixin(BaseApiMixin):
    def resize_window(self, width, height):
        if self._window:
            self._window.resize(width, height)
    
    def move_window(self, x, y):
        if self._window:
            self._window.move(x, y)

    def get_window_pos(self):
        if self._window:
            return {"x": self._window.x, "y": self._window.y}
        return {"x": 0, "y": 0}

    def close_window(self):
        if self._window:
            self._window.destroy()
        sys.exit()

    def open_settings(self):
        # Create a new independent window for settings
        import webview
        import os
        
        # Resolve path
        # src/api/window_api.py -> src/api -> src -> root -> dist/settings.html
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'dist', 'settings.html'))
        
        # Check if already open
        if SETTINGS_WINDOW_REF["window"]:
             try:
                 SETTINGS_WINDOW_REF["window"].restore()
                 SETTINGS_WINDOW_REF["window"].focus()
                 return
             except:
                 SETTINGS_WINDOW_REF["window"] = None

        new_window = webview.create_window(
            'SoulMate Settings', 
            url=settings_path,
            js_api=self, # Share API instance
            width=800,
            height=700,
            resizable=True,
            on_top=True
        )
        SETTINGS_WINDOW_REF["window"] = new_window

    def close_settings(self):
        """Closes the settings window if open."""
        if SETTINGS_WINDOW_REF["window"]:
            try:
                SETTINGS_WINDOW_REF["window"].destroy()
            except:
                pass
            SETTINGS_WINDOW_REF["window"] = None
    
    def close_app(self):
        self.close_window()
