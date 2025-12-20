import google.generativeai as genai
import json
import os

# Load Settings
try:
    with open('settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
        api_key = settings.get('api_key')
        model_name = settings.get('model_name', 'gemini-1.5-flash')
except Exception as e:
    print(f"Failed to load settings: {e}")
    exit(1)

print(f"Testing Model: {model_name}")

if not api_key:
    print("No API Key found.")
    exit(1)

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={"response_mime_type": "application/json"}
    )
    prompt = """
    Return a JSON object with a greeting.
    { "greeting": "Hello" }
    """
    response = model.generate_content(prompt)
    print(f"Response Raw: '{response.text}'")
    
    try:
        import json
        data = json.loads(response.text)
        print("JSON Parsed:", data)
        print("SUCCESS")
    except Exception as e:
        print(f"JSON Parse Failed: {e}")
except Exception as e:
    print(f"FAILED: {e}")
