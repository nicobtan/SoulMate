
import os
import sys

sys.path.append(os.getcwd())
from src.core.config_manager import ConfigManager
from google import genai

cm = ConfigManager()
# ConfigManager key is "api_key" based on cat output
api_key = cm.get("api_key")

if not api_key:
    # Fallback to key.json just in case
    try:
        import json
        with open("key.json", "r") as f:
            api_key = json.load(f)["key"]
    except:
        pass

if not api_key:
    print("No API Key found anywhere.")
    sys.exit(1)

client = genai.Client(api_key=api_key)
try:
    print("Listing models...")
    for m in client.models.list(config={"page_size": 100}):
        if "gemini" in m.name:
            print(f"- {m.name}")
            
    # Also check specific model availability if possible
    try:
        client.models.get(model="models/gemini-2.0-flash-lite-preview-02-05")
        print("✅ gemini-2.0-flash-lite-preview-02-05 EXISTS")
    except:
        print("❌ gemini-2.0-flash-lite-preview-02-05 NOT FOUND")

except Exception as e:
    print(f"Error: {e}")
