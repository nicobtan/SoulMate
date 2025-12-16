from src.services.ai_engine import AIEngine
from src.core.config_manager import ConfigManager
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

print("--- Testing AIEngine (New SDK) ---")

cm = ConfigManager()
api_key = cm.get("api_key")

if not api_key:
    print("No API Key found.")
    exit()

engine = AIEngine()
engine.configure(api_key=api_key)

print("\n1. Testing Chat (Simple Hello)...")
try:
    response = engine.generate_response("Hello, who are you?")
    print(f"Response: {response}")
except Exception as e:
    print(f"Chat Error: {e}")

print("\n2. Testing Grounding (Manual)...")
try:
    # We ask something that requires grounding about Python 3.13
    response = engine.generate_response("What is the release date of Python 3.14?")
    print(f"Response: {response}")
except Exception as e:
    print(f"Grounding Error: {e}")

print("\n3. Testing Proactive Message...")
try:
    response = engine.generate_proactive_message("User is studying AI.")
    print(f"Response: {response}")
except Exception as e:
    print(f"Proactive Error: {e}")
