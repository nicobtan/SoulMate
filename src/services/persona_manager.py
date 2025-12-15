import os
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersonaManager:
    def __init__(self, persona_dir="personas"):
        # Handle path resolution (exe vs script)
        if hasattr(os, '_MEIPASS'):
            import sys
            base_dir = sys._MEIPASS
        else:
            # Current file is in src/services/. Project root is ../../
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        self.persona_dir = os.path.join(base_dir, persona_dir)
        if not os.path.exists(self.persona_dir):
            try:
                os.makedirs(self.persona_dir)
                logger.warning(f"Persona directory created at: {self.persona_dir}")
            except Exception as e:
                logger.error(f"Failed to create persona directory: {e}")

    def list_personas(self):
        """Returns a list of available persona filenames (without extension)."""
        personas = []
        if not os.path.exists(self.persona_dir):
            return []
            
        for filename in os.listdir(self.persona_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                personas.append(os.path.splitext(filename)[0])
        return personas

    def load_persona(self, persona_id):
        """Loads a specific persona YAML file and returns the dictionary."""
        # Strip extension if accidentally passed
        if persona_id.endswith('.yaml'):
            persona_id = persona_id[:-5]
        elif persona_id.endswith('.yml'):
            persona_id = persona_id[:-4]

        # Try .yaml first, then .yml
        filepath = os.path.join(self.persona_dir, f"{persona_id}.yaml")

        if not os.path.exists(filepath):
            filepath = os.path.join(self.persona_dir, f"{persona_id}.yml")
            
        if not os.path.exists(filepath):
            logger.error(f"Persona file not found: {filepath}")
            # Fallback to default if not default
            if persona_id != "default":
                logger.info("Falling back to default persona.")
                return self.load_persona("default")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data
        except Exception as e:
            logger.error(f"Failed to load persona {persona_id}: {e}")
            return None
