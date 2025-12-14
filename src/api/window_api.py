import sys
from .base import BaseApiMixin

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
        
        webview.create_window(
            'SoulMate Settings', 
            url=settings_path,
            js_api=self, # Share API instance
            width=600,
            height=600,
            resizable=False,
            on_top=True
        )
    
    def close_app(self):
        self.close_window()
