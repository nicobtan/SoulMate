from .base import BaseApiMixin

class SettingsApiMixin(BaseApiMixin):
    def get_settings(self):
        return self._config_manager.get_all()

    def save_settings(self, settings):
        self._config_manager.update(settings)
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

        return {"status": "success", "settings": self._config_manager.get_all()}
    
    def get_persona_list(self):
        return self._persona_manager.list_personas()

    def change_persona(self, persona_id):
        """Switches the current persona."""
        data = self._persona_manager.load_persona(persona_id)
        
        if not data:
            return {"status": "error", "message": "Persona not found"}
            
        self._ai_engine.set_system_prompt(data.get('system_prompt', ''))
        
        # Save to Config
        self._config_manager.config['current_persona_id'] = persona_id
        self._config_manager.save()
        
        return {"status": "success", "name": data.get('name', persona_id)}

    def get_voice_types(self):
        # Return hardcoded list for now, or fetch from Google API
        return [
            {"id": "ja-JP-Neural2-B", "name": "女性 (Neural2-B) - 明るい"},
            {"id": "ja-JP-Neural2-C", "name": "男性 (Neural2-C) - 落ち着いた"},
            {"id": "ja-JP-Neural2-A", "name": "女性 (Neural2-A) - アナウンサー風"},
            {"id": "ja-JP-Standard-A", "name": "女性 (Standard-A) - 標準"},
        ]

    def get_calendar_status(self):
        if self._calendar_manager:
            return self._calendar_manager.is_authenticated
        return False

    def authenticate_calendar(self):
        if self._calendar_manager:
            return self._calendar_manager.authenticate()
        return False
        
    def save_window_position(self):
        """Saves current window position to config."""
        if self._window:
            x, y = self._window.x, self._window.y
            self._config_manager.update({'window_x': x, 'window_y': y})
            return {"status": "success", "x": x, "y": y}
        return {"status": "error", "message": "Window not found"}

    def _configure_ai(self, settings):
        """Updates AI Engine and Persona based on settings."""
        if not self._config_manager or not self._ai_engine or not self._persona_manager:
            return

        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        
        # Get Persona Content
        persona_id = settings.get('current_persona_id', 'default')
        # Handle legacy 'current_persona_file' if present (strip extension)
        if 'current_persona_file' in settings:
            persona_id = settings['current_persona_file'].replace('.yaml', '').replace('.yml', '')
            
        profile = self._persona_manager.load_persona(persona_id)
        
        # Update AI
        self._ai_engine.configure(api_key, model)
        
        if profile:
            self._ai_engine.set_system_prompt(profile.get('system_prompt', ''))

    
    def get_search_topics(self):
        """Returns search topics as a single string (newline separated)."""
        try:
            if hasattr(self, 'interest_manager') and self.interest_manager:
                topics = self.interest_manager.load_topics()
                return "\n".join(topics)
        except Exception as e:
            print(f"Error getting search topics: {e}")
        return ""

    def save_search_topics(self, topics_str):
        """Saves newline separated topics."""
        if hasattr(self, 'interest_manager') and self.interest_manager:
            topics_list = topics_str.split('\n')
            self.interest_manager.save_topics(topics_list)
            return {"status": "success"}
        return {"status": "error", "message": "InterestManager not initialized"}
