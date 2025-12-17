import os
import json
from google import genai
from src.core.config_manager import ConfigManager

def list_models():
    cm = ConfigManager()
    settings = cm.get_all()
    api_key = settings.get('api_key')
    
    if not api_key:
        print("No API Key found.")
        return

    client = genai.Client(api_key=api_key)
    
    print("--- Gemini Models (Clean) ---")
    try:
        for m in client.models.list():
            if "gemini" in m.name.lower():
                 print(m.name.strip())
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
