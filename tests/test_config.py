from src.config_manager import ConfigManager
import os
import json

def test_config_manager():
    print("Testing ConfigManager...")
    
    # Initialize
    config = ConfigManager(filename='test_settings.json')
    print(f"Config path: {config.filepath}")
    
    # Check default values
    assert config.get("model") == "gemini-1.5-flash"
    print("Default value check passed.")
    
    # Test Update
    config.set("api_key", "TEST_KEY_123")
    config.set("font_size", 20)
    print("Values updated in memory.")
    
    # Verify Save (File should exist)
    if os.path.exists(config.filepath):
        print("File created successfully.")
        with open(config.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert data["api_key"] == "TEST_KEY_123"
            assert data["font_size"] == 20
        print("File content verification passed.")
    else:
        print("ERROR: File was not created.")
        return

    # Clean up
    os.remove(config.filepath)
    print("Test cleanup done.")
    print("ConfigManager verification SUCCESS!")

if __name__ == "__main__":
    test_config_manager()
