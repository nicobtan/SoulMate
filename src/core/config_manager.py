import json
import os
import sys

class ConfigManager:
    """
    Manages application settings and persistence to settings.json.
    """
    def __init__(self, filename='settings/config.json'):
        # Determine the base path (handle creating in the correct directory)
        if hasattr(sys, '_MEIPASS'):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up levels to root: core -> src -> root
            while os.path.basename(self.base_dir) in ['core', 'src']:
                self.base_dir = os.path.dirname(self.base_dir)
        
        self.filepath = os.path.join(self.base_dir, filename)
        self.config = self._load_default_config()
        self.load()

    def _load_default_config(self):
        """Returns the default configuration dictionary."""
        return {
            "api_key": "",
            "model": "gemini-1.5-flash",
            "background_opacity": 0,
            "font_size": 13,
            "max_balloons": 3,
            "current_persona_id": "default",
            "personas": {
                "default": {
                    "name": "SoulMate",
                    "system_instruction": "You are a helpful and cute AI assistant."
                }
            },
            "proactive_vision_interval_min": 5,
            "proactive_silent_mode": False,
            "proactive_targets": ["work", "media", "health"],
            "dify_api_key": ""
        }

    def load(self):
        """Loads configuration from the file. Creates default if not exists."""
        print(f"[ConfigManager] Loading from {self.filepath}")
        if not os.path.exists(self.filepath):
            print("[ConfigManager] File not found, saving default.")
            self.save()
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Merge with default to ensure all keys exist (simple migration)
                for key, value in self._load_default_config().items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                self.config = loaded_config
                print(f"[ConfigManager] Loaded Config: current_character_id={self.config.get('current_character_id')}")
        except Exception as e:
            print(f"Error loading config: {e}")
            # Fallback to default but keep in memory
            pass

    def save(self):
        """Saves the current configuration to the file."""
        try:
            print(f"[ConfigManager] Saving Config: current_character_id={self.config.get('current_character_id')}")
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        """Retrieves a configuration value."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Sets a configuration value and saves to file."""
        self.config[key] = value
        self.save()

    def update(self, new_settings):
        """Updates multiple settings at once and saves."""
        self.config.update(new_settings)
        self.save()

    def get_all(self):
        """Returns the entire configuration dictionary."""
        return self.config
