import sys
import os
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_grounding")

print("--- Starting Debug ---")

# 1. Test YAML Import
try:
    import yaml
    print(f"PyYAML imported successfully. Version: {yaml.__version__}")
except ImportError as e:
    print(f"CRITICAL: PyYAML not found! {e}")
except Exception as e:
    print(f"Error importing yaml: {e}")

# 2. Test InterestManager
try:
    from src.services.interest_manager import InterestManager
    im = InterestManager("search_topics.yaml")
    print("InterestManager instantiated.")
    topics = im.load_topics()
    print(f"Loaded Topics: {topics}")
except Exception as e:
    print(f"InterestManager Error: {e}")

# 3. Test Google GenAI Import and Config
try:
    import google.generativeai as genai
    print(f"google-generativeai version: {genai.__version__}")
    
    # Configure (Mock key if needed, or use env)
    # We need a key to test init
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("WARNING: GOOGLE_API_KEY not in env. Skipping actual Model init test with key.")
        # Try finding key in ConfigManager
        try:
             from src.core.config_manager import ConfigManager
             cm = ConfigManager()
             key = cm.get("api_key")
             print(f"Found Key in Config: {key[:5]}...")
        except:
             pass

    if key:
        genai.configure(api_key=key)
        
        # Test Tools Config Syntax
        print("Testing Tools Configuration Syntax...")
        
        # Method 1: Dictionary
        tools = [{"google_search": {}}]
        
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp", # Use a known grounding-capable model
                tools=tools
            )
            print("GenerativeModel initialized with google_search (Dict way) - Success")
        except Exception as e:
            print(f"GenerativeModel Init Failed (Dict way): {e}")

except Exception as e:
    print(f"GenAI Error: {e}")

print("--- Debug Finished ---")
