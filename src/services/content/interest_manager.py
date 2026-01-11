import yaml
import os

class InterestManager:
    def __init__(self, topics_path="search_topics.yaml"):
        self.topics_path = topics_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.topics_path):
            self.save_topics(["Python programming", "Artificial Intelligence news"])

    def load_topics(self):
        """Returns a list of topic strings."""
        try:
            with open(self.topics_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data and 'topics' in data:
                    raw_topics = data['topics']
                    
                    # Flatten logic if categorized (dict)
                    if isinstance(raw_topics, dict):
                        flattened = []
                        for category, items in raw_topics.items():
                            if isinstance(items, list):
                                flattened.extend(items)
                        return flattened
                    
                    # Legacy list support
                    elif isinstance(raw_topics, list):
                        return raw_topics
                return []
        except Exception as e:
            print(f"Error loading search topics: {e}")
            return []

    def save_topics(self, topics_list):
        """Saves a list of topic strings."""
        try:
            # Filter empty
            topics_list = [t for t in topics_list if t.strip()]
            data = {'topics': topics_list}
            with open(self.topics_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving search topics: {e}")
            return False

    def get_raw_yaml(self):
        """Returns raw yaml string."""
        try:
            with open(self.topics_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def save_raw_yaml(self, yaml_content):
        """Saves raw yaml string."""
        try:
            # Validate YAML first
            yaml.safe_load(yaml_content)
            with open(self.topics_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            return True
        except Exception as e:
            print(f"Invalid YAML: {e}")
            return False
