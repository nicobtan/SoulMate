import os
from google import genai
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # try reading from config.json
    import json
    with open("settings/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        api_key = config.get("api_key")

print("API Key loaded:", "Yes" if api_key else "No")

client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-flash-lite-preview-tts",
    "gemini-2.5-pro-preview-tts"
]

text = "えるくん、お茶にしませんか〜？それとも、何か他にお話ししたいこと、ありますか…？"

for model_id in models_to_test:
    print(f"\n--- Testing Model: {model_id} ---")
    try:
        response = client.models.generate_content(
            model=f"models/{model_id}",
            contents=[text],
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Aoede"
                        )
                    )
                )
            )
        )
        print(f"Success! Response parts: {len(response.parts)}")
    except Exception as e:
        print(f"Failed: {e}")

