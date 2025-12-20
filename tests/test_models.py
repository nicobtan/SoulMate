import google.generativeai as genai
import os
from src.core.config_manager import ConfigManager

cm = ConfigManager()
api_key = cm.get("api_key")

if not api_key:
    print("No API Key found.")
    exit()

genai.configure(api_key=api_key)

print("--- Listing Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- Testing Specific Models ---")
models_to_test = [
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "models/gemini-2.0-flash-exp",
    "gemini-2.0-flash-exp"
]

for m_name in models_to_test:
    print(f"Testing {m_name}...", end=" ")
    try:
        model = genai.GenerativeModel(m_name)
        # Try a simple generation (mocking tools if needed, but just init first)
        response = model.generate_content("Hello")
        print("Success")
    except Exception as e:
        print(f"Failed: {e}")
