import os
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaManager:
    def __init__(self, persona_dir="test_persona"):
        # Handle path resolution (exe vs script)
        if hasattr(os, '_MEIPASS'):
            import sys
            base_dir = sys._MEIPASS
        else:
            # Assuming this file is in src/, go up one level
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.persona_dir = os.path.join(base_dir, persona_dir)
        if not os.path.exists(self.persona_dir):
            os.makedirs(self.persona_dir)
            logger.warning(f"Persona directory created at: {self.persona_dir}")

    def list_personas(self):
        """Returns a list of available persona filenames (without extension if possible, or simple names)."""
        personas = []
        if not os.path.exists(self.persona_dir):
            return []
            
        for filename in os.listdir(self.persona_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                personas.append(filename)
        return personas

    def load_persona(self, filename):
        """Loads a specific persona YAML file and returns the dictionary."""
        filepath = os.path.join(self.persona_dir, filename)
        if not os.path.exists(filepath):
            logger.error(f"Persona file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load persona {filename}: {e}")
            return None
