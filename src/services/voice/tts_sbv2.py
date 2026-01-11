import requests
import io
import soundfile as sf
import sounddevice as sd

class StyleBertVITS2Client:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.api_url = f"{self.base_url}/voice"
        self.default_params = {
            "model_id": 0,
            "speaker_id": 0,
            "sdp_ratio": 0.2,
            "noise": 0.6,
            "noisew": 0.8,
            "length": 1.0,
            "language": "JP",
            "style": "Neutral",
        }

    def speak(self, text, style="Neutral"):
        params = self.default_params.copy()
        params["text"] = text
        
        # スタイル名の正規化 (先頭大文字)
        style = style.capitalize()
        valid_styles = ["Neutral", "Happy", "Angry", "Sad", "Whisper"]
        if style not in valid_styles:
            style = "Neutral"
        params["style"] = style

        try:
            print(f"🎤 [SBV2] Request: '{text[:10]}...' (Style: {style})")
            # CPUモード対策でタイムアウト長め(30秒)
            res = requests.get(self.api_url, params=params, timeout=30)

            if res.status_code == 200:
                data, samplerate = sf.read(io.BytesIO(res.content))
                sd.play(data, samplerate)
                sd.wait()
                return True
            else:
                print(f"❌ [SBV2] Error: {res.status_code}")
                return False
        except Exception as e:
            print(f"❌ [SBV2] Connection Failed: {e}")
            return False