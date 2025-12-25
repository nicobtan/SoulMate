import requests
import io
import soundfile as sf
import sounddevice as sd

# ローカルサーバーのURL
url = "http://127.0.0.1:5000/voice"

# 話させる内容
params = {
    "text": "えるくん、聞こえていますか？ RTX 5060 Tiの力、ついに解放です！",
    "model_id": 0,    # 0番目のモデル(jvnv)
    "speaker_id": 0,
    "sdp_ratio": 0.2,
    "noise": 0.6,
    "noisew": 0.8,
    "length": 1.0,
    "language": "JP",
    "style": "Neutral",
}

print("生成リクエスト送信中...")
res = requests.get(url, params=params)

if res.status_code == 200:
    print("再生します！🔊")
    data, samplerate = sf.read(io.BytesIO(res.content))
    sd.play(data, samplerate)
    sd.wait()
else:
    print("エラー:", res.text)