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
        if provider == "gemini":
            return self._generate_gemini_audio(text, voice_name)
            
        # Default to VOICEVOX
        return self._generate_voicevox_audio(text, voice_name)

    def _generate_gemini_audio(self, text: str, voice_name: str) -> str:
        if not self.genai_client:
            logger.error("GenAI Client not ready. API Key missing.")
            return None

        try:
            start_time = time.time()
            # モデル名: ドキュメント準拠のFlash Preview版
            model_id = "gemini-2.5-flash-preview-tts"
            
            logger.info(f"Generating Audio via Gemini TTS... (Model: {model_id}, Voice: {voice_name})")
            
            # 1. API Call
            # SDKの制約上、現在はRaw PCMが返ってくるため、フォーマット指定は行わずデフォルトを受け取ります
            response = self.genai_client.models.generate_content(
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
            
            # 2. 音声データの抽出
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
            
            return final_web_path

        except Exception as e:
            logger.error(f"Gemini TTS Error: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            return None
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None
