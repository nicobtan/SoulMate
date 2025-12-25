import logging
import time
import os
import re
import wave
import urllib.parse
from google import genai
from google.genai import types

logger = logging.getLogger("tts_gemini")

class GeminiTTSClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.client = None
        self.output_dir = os.path.join("dist", "audio")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        if self.api_key:
            self._init_client(self.api_key)

    def set_api_key(self, api_key):
        self.api_key = api_key
        self._init_client(api_key)

    def _init_client(self, api_key):
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info("GeminiTTSClient: Client Initialized")
        except Exception as e:
            logger.error(f"GeminiTTSClient: Init Failed: {e}")

    def generate_audio(self, text, voice_name="Aoede"):
        if not self.client:
            logger.error("GenAI Client not ready. API Key missing.")
            return None

        try:
            start_time = time.time()
            model_id = "gemini-2.5-flash-preview-tts"
            
            logger.info(f"Generating Audio via Gemini TTS... (Model: {model_id}, Voice: {voice_name})")
            
            # 1. API Call
            response = self.client.models.generate_content(
                model=model_id,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
            
            # 2. Extract Audio
            audio_data = None
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        audio_data = part.inline_data.data
                        break
            
            if not audio_data and hasattr(response, 'bytes'):
                audio_data = response.bytes
            
            if not audio_data:
                logger.error("Gemini TTS Error: No audio data found.")
                return None

            # 3. Filename
            safe_text = re.sub(r'[\\/:*?"<>|]+', '', text)
            safe_text = re.sub(r'\s+', '_', safe_text)
            safe_text = safe_text[:20]
            
            filename = f"voice_{int(time.time())}_{safe_text}.wav"
            filepath = os.path.join(self.output_dir, filename)
            
            # 4. Save
            is_wav = audio_data[:4] == b'RIFF'
            if is_wav:
                with open(filepath, "wb") as f:
                    f.write(audio_data)
            else:
                try:
                    with wave.open(filepath, 'wb') as wf:
                        wf.setnchannels(1) 
                        wf.setsampwidth(2) 
                        wf.setframerate(24000) 
                        wf.writeframes(audio_data)
                except Exception as e:
                    logger.error(f"WAV Convert Error: {e}")
                    return None

            # 5. Return Web Path
            encoded_name = urllib.parse.quote(filename)
            final_web_path = f"audio/{encoded_name}"
            
            duration = time.time() - start_time
            logger.info(f"[TTS] Gemini Audio Generated in {duration:.3f}s: {filename}")
            
            return final_web_path

        except Exception as e:
            logger.error(f"Gemini TTS Error: {e}")
            return None
