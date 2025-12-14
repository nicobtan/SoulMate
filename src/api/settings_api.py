from .base import BaseApiMixin

class SettingsApiMixin(BaseApiMixin):
    def get_settings(self):
        return self.config_manager.get_all()

    def save_settings(self, settings):
        self.config_manager.update(settings)
        # Re-configure AI
        self._configure_ai(settings)
        
        # Re-configure Active Engine
        if hasattr(self, 'active_engine') and self.active_engine:
            self.active_engine.configure(settings)
        
        # Apply visual settings to Main Window immediately
        if self._window:
            # Opacity
            opacity = settings.get('bg_opacity', 0)
            self._window.evaluate_js(f"document.body.style.backgroundColor = 'rgba(0,0,0,{opacity/100})'")
            # Font Size
            font_size = settings.get('font_size', 13)
            self._window.evaluate_js(f"document.documentElement.style.setProperty('--chat-font-size', '{font_size}px')")

        return {"status": "success", "settings": self.config_manager.get_all()}
    
    def get_personas(self):
        return self.persona_manager.list_personas()

    def get_voice_types(self):
        # Return hardcoded list for now, or fetch from Google API
        return [
            {"id": "ja-JP-Neural2-B", "name": "女性 (Neural2-B) - 明るい"},
            {"id": "ja-JP-Neural2-C", "name": "男性 (Neural2-C) - 落ち着いた"},
            {"id": "ja-JP-Neural2-A", "name": "女性 (Neural2-A) - アナウンサー風"},
            {"id": "ja-JP-Standard-A", "name": "女性 (Standard-A) - 標準"},
        ]

    def get_calendar_status(self):
        if self.calendar_manager:
            return self.calendar_manager.is_authenticated
        return False

    def authenticate_calendar(self):
        if self.calendar_manager:
            return self.calendar_manager.authenticate()
        return False
        
    def save_window_position(self):
        """Saves current window position to config."""
        if self._window:
            x, y = self._window.x, self._window.y
            self.config_manager.update({'window_x': x, 'window_y': y})
            return {"status": "success", "x": x, "y": y}
        return {"status": "error", "message": "Window not found"}

    def _configure_ai(self, settings):
        """Updates AI Engine and Persona based on settings."""
        if not self.config_manager or not self.ai_engine or not self.persona_manager:
            return

        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        
        # Get Persona Content
        persona_file = settings.get('current_persona_file', 'default')
        profile = self.persona_manager.load_persona(persona_file)
        
        # Update AI
        self.ai_engine.configure(api_key, model, profile_data=profile)
