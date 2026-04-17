import requests
import os
import time
import logging
import re
import wave
import urllib.parse
from google import genai
from google.genai import types

logger = logging.getLogger("voice_service")

class VoiceService:
    def __init__(self):
        self.base_url = "http://127.0.0.1:50021"
        self.output_dir = os.path.join("dist", "audio") 
        self.genai_client = None
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def set_api_key(self, api_key: str):
        """Initializes GenAI client with the provided API key."""
        if api_key:
            try:
                self.genai_client = genai.Client(api_key=api_key)
                logger.info("VoiceService: GenAI Client Initialized for Gemini TTS")
            except Exception as e:
                logger.error(f"VoiceService: Failed to init GenAI Client: {e}")

    def generate_voice(self, text: str, voice_name: str = "3", provider: str = "voicevox") -> str:
        """
        Generates audio for the given text.
        Returns the relative path (e.g. 'audio/filename.wav').
        """
        if "gemini" in provider:
            # provider string is the model_id (e.g., "gemini-2.5-pro-tts")
            return self._generate_gemini_audio(text, voice_name, model_id=provider)
            
        # Default to VOICEVOX
        return self._generate_voicevox_audio(text, voice_name)

    def _generate_gemini_audio(self, text: str, voice_name: str, model_id: str) -> str:
        if not self.genai_client:
            logger.error("GenAI Client not ready. API Key missing.")
            return None

        try:
            start_time = time.time()
            # model_id is passed from settings (provider)
            
            # Legacy/Fallback check if 'gemini' generic string passed
            if model_id == "gemini":
                model_id = "gemini-2.5-flash-preview-tts"

            # Auto-Correct: User specified "gemini-2.5-flash-tts" but API expects "gemini-2.5-flash-preview-tts"
            if model_id == "gemini-2.5-flash-tts":
                logger.info("VoiceService: Correcting 'gemini-2.5-flash-tts' to 'gemini-2.5-flash-preview-tts'")
                model_id = "gemini-2.5-flash-preview-tts"

            # Sanitize Voice Name
            if voice_name.isdigit() or len(voice_name) < 2:
                voice_name = "Aoede" # Default to Female-sounding
                logger.info("VoiceService: Numeric voice name detected. Defaulting to 'Aoede' for Gemini.")

            logger.info(f"Generating Audio via Gemini TTS... (Model: {model_id}, Voice: {voice_name})")
            print(f"[AUDIO DEBUG] Generating Audio via Gemini TTS... (Voice: {voice_name}, Model: {model_id})")
            
            # 0. Text Cleaning (User Recommendation)
            # Remove emojis and special symbols that may cause 500/400 errors in preview models
            import re
            clean_text = text.replace('〜', 'ー').replace('～', 'ー')
            clean_text = clean_text.replace('…', '。').replace('♪', '。')
            clean_text = re.sub(r'[^\w\sぁ-んァ-ヶー一-龠、。！？]', '', clean_text)
            clean_text = clean_text.strip()
            
            if not clean_text:
                logger.warning("TTS: Input text became empty after cleaning.")
                return None

            # 1. API Call with Retry Loop
            max_retries = 3
            base_delay = 1.0
            response = None
            
            for attempt in range(max_retries):
                try:
                    actual_model = f"models/{model_id}" if not model_id.startswith("models/") else model_id
                    response = self.genai_client.models.generate_content(
                        model=actual_model,
                        contents=[clean_text],
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
                    break # Success
                except Exception as api_error:
                    error_msg = str(api_error)
                    is_retryable = any(code in error_msg for code in ["500", "503", "429", "INTERNAL", "UNAVAILABLE", "ResourceExhausted"])
                    
                    if is_retryable and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"VoiceService: Gemini TTS transient error (Attempt {attempt+1}/{max_retries}): {error_msg}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        raise api_error
            
            # 2. 音声データの抽出
            audio_data = None
            
            # Debug: Log the raw response structure to understand why parts might be empty
            logger.info(f"Gemini Response Keys: {dir(response)}")
            try:
                # Check directly if candidates exist (New SDK pattern)
                if hasattr(response, 'candidates') and response.candidates:
                    c = response.candidates[0]
                    if hasattr(c, 'content') and c.content and hasattr(c.content, 'parts'):
                        for part in c.content.parts:
                            if part.inline_data:
                                logger.info(f"Found Inline Data. Mime: {part.inline_data.mime_type}")
                                audio_data = part.inline_data.data
                                break
            except Exception as e:
                logger.error(f"Candidate parsing failed: {e}")

            # Fallback/Shortcut 'response.parts' check
            if not audio_data and hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if part.inline_data:
                        audio_data = part.inline_data.data
                        break
            
            # response.bytes fallback (unlikely but kept)
            if not audio_data and hasattr(response, 'bytes'):
                audio_data = response.bytes

            
            if not audio_data:
                logger.error("Gemini TTS Error: No audio data found.")
                return None

            # 3. ファイル名生成（日本語対応）
            safe_text = re.sub(r'[\\/:*?"<>|]+', '', text)
            safe_text = re.sub(r'\s+', '_', safe_text)
            safe_text = safe_text[:20]
            
            # Extension .wav
            filename = f"voice_{int(time.time())}_{safe_text}.wav"
            filepath = os.path.join(self.output_dir, filename)
            
            # 4. Smart Save (Check for RIFF header)
            # If it starts with 'RIFF', it's already a WAV. Don't add header.
            is_wav = audio_data[:4] == b'RIFF'
            
            if is_wav:
                try:
                    with open(filepath, "wb") as f:
                        f.write(audio_data)
                except Exception as e:
                    logger.error(f"WAV Save Error: {e}")
                    return None
            else:
                # Raw PCM -> Add Header
                try:
                    with wave.open(filepath, 'wb') as wf:
                        wf.setnchannels(1)      # モノラル
                        wf.setsampwidth(2)      # 16-bit
                        wf.setframerate(24000)  # サンプリングレート 24kHz
                        wf.writeframes(audio_data)
                except Exception as e:
                    logger.error(f"WAV Convert Error: {e}")
                    return None

            # 5. フロントエンド用のパス生成（URLエンコード）
            encoded_name = urllib.parse.quote(filename)
            final_web_path = f"audio/{encoded_name}"
            
            # Timer Log
            duration = time.time() - start_time
            logger.info(f"[TTS] Gemini Audio Generated in {duration:.3f}s: {filename} (WAV)")
            print(f"[AUDIO DEBUG] ✅ Audio Generated: {filename} ({duration:.3f}s)")
            
            return final_web_path

        except Exception as e:
            logger.error(f"Gemini TTS Error: {e}")
            
            # Detailed Debugging for 404/400
            if "404" in str(e) or "400" in str(e):
                print("\n[DEBUG] --- Available Gemini Models for this API Key ---")
                try:
                    # Generic listing
                    for m in self.genai_client.models.list(config={'page_size': 100}):
                        # Filter for likely candidates
                        name = getattr(m, 'name', str(m))
                        if "gemini" in name or "flash" in name:
                            print(f"- {name}")
                except Exception as le:
                    print(f"Failed to list models: {le}")
                print("----------------------------------------------------\n")

            # Re-raise to allow ChatApi to log this to the UI
            raise e

    def _generate_voicevox_audio(self, text: str, voice_name: str) -> str:
        try:
            speaker_id = int(voice_name)
        except ValueError:
            speaker_id = 3 # Default to Zundamon Normal
            
        try:
            # 1. Query Creation
            query_payload = {"text": text, "speaker": speaker_id}
            r_query = requests.post(f"{self.base_url}/audio_query", params=query_payload)
            
            if r_query.status_code != 200:
                logger.error(f"VOICEVOX Query Error: {r_query.text}")
                return None
            
            query_data = r_query.json()

            # 2. Synthesis
            r_synth = requests.post(f"{self.base_url}/synthesis", params={"speaker": speaker_id}, json=query_data)
            if r_synth.status_code != 200:
                logger.error("VOICEVOX Synthesis Error")
                return None

            # 3. Save File
            filename = f"voice_{int(time.time())}.wav"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(r_synth.content)
            
            return f"audio/{filename}"

        except requests.exceptions.ConnectionError:
            logger.warning("VOICEVOX is not running on port 50021. Please start VOICEVOX.")
            raise Exception("VOICEVOX Connection Error: Is the Engine running?")
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            raise e
