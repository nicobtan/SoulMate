import sys
import os

# Set paths
sys.path.append(os.getcwd())

from main import Api

# Mock webview window
class MockWindow:
    def __init__(self):
        self.events = self
        self.loaded = self # dummy event
        self._on_top = False

    def evaluate_js(self, js):
        print(f"[MockWindow] evaluate_js: {js}")
    
    @property
    def on_top(self):
        return self._on_top
    
    @on_top.setter
    def on_top(self, value):
        print(f"[MockWindow] Setting on_top to {value}")
        self._on_top = value
    
    def create_file_dialog(self, **kwargs):
        return None

    def __iadd__(self, other):
        return self

try:
    print("Initializing API...")
    api = Api()
    # Mock window
    api._window = MockWindow()
    api._config_manager.config['always_on_top'] = True # Reset to default for test
    
    # Check initial
    initial_val = api._config_manager.get('always_on_top')
    print(f"Initial always_on_top: {initial_val}")

    # Save settings with always_on_top = False
    new_settings = api._config_manager.get_all().copy()
    new_settings['always_on_top'] = False
    print("Saving settings with always_on_top=False...")
    
    api.save_settings(new_settings)

    # Check config again
    post_save_val = api._config_manager.get('always_on_top')
    print(f"Post-save always_on_top: {post_save_val}")

    # Check File persistence
    import json
    with open('settings/config.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"File persisted value: {data.get('always_on_top')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
