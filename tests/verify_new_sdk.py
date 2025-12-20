import os
import sys

print("Checking google-genai...")
try:
    from google import genai
    from google.genai import types
    print("New SDK imported successfully.")
except ImportError:
    print("New SDK not found. Install 'google-genai'.")
    sys.exit(1)

from src.core.config_manager import ConfigManager
cm = ConfigManager()
api_key = cm.get("api_key")

if not api_key:
    print("No API Key.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

print("--- Testing Grounding with gemini-2.5-flash-lite ---")

# Tool Config
grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

# Test Message
prompt = "What is the latest news about Python 3.13?"

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[grounding_tool],
            response_mime_type="text/plain" 
        )
    )
    
    print("Response Received!")
    print(f"Text: {response.text[:200]}...")
    
    if response.candidates[0].grounding_metadata:
        print("Grounding Metadata Found!")
        search_entry = response.candidates[0].grounding_metadata.search_entry_point
        if search_entry:
            print(f"Search HTML: {search_entry.rendered_content[:100]}...")
    else:
        print("No Grounding Metadata.")

except Exception as e:
    print(f"Error: {e}")
