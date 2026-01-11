import os
import uuid
from google.cloud import texttospeech

class TTSEngine:
    def __init__(self, key_path=None):
        if key_path:
            # Set the environment variable for Google Cloud credentials
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        
        try:
            self.client = texttospeech.TextToSpeechClient()
            print("TTS Engine initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize TTS Engine: {e}")
            self.client = None

    def generate_voice(self, text, output_dir="dist/audio", voice_name="ja-JP-Neural2-B", pitch=2.0, rate=1.1):
        """
        Generates audio for the given text using specified voice settings.
        Returns the relative path to the audio file.
        """
        if not self.client:
            print("TTS Client not available.")
            return None
            
        if not text:
            return None

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Voice Configuration
            voice = texttospeech.VoiceSelectionParams(
                language_code="ja-JP",
                name=voice_name
            )

            # Audio Configuration
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                pitch=pitch,
                speaking_rate=rate
            )

            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Ensure output directory exists
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Generate unique filename to avoid caching issues
            filename = f"voice_{uuid.uuid4().hex}.mp3"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "wb") as out:
                out.write(response.audio_content)
                print(f"Audio content written to file {filepath}")
            
            # Return relative path for frontend (assuming dist is root)
            # output_dir is "dist/audio", so relative path is "audio/filename"
            return f"audio/{filename}"

        except Exception as e:
            print(f"TTS Generation failed: {e}")
            return None
