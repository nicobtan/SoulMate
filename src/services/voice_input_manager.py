import os
import threading
import time
import tempfile
import wave
import wave
import pyaudio
import logging
import keyboard
from faster_whisper import WhisperModel

# ロガー設定
logger = logging.getLogger("voice_manager")
logging.basicConfig(level=logging.INFO)

class VoiceInputManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(VoiceInputManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.record_thread = None
        self.model = None
        
        # 設定 (デフォルト)
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000 # Whisper推奨レート
        
        # モデルの遅延ロード
        self.model_size = "base" 
        self.device = "cuda" # GPUがある場合。なければ "cpu"
        self.compute_type = "float16" # CPUなら "int8"
        
        self.current_hotkey = None

    def set_hotkey(self, hotkey_str, callback):
        """グローバルホットキーを設定する"""
        try:
            # 既存の登録を解除
            if self.current_hotkey:
                try:
                    keyboard.remove_hotkey(self.current_hotkey)
                except:
                    pass
                self.current_hotkey = None
            
            if not hotkey_str:
                return

            logger.info(f"Registering Hotkey: {hotkey_str}")
            keyboard.add_hotkey(hotkey_str, callback)
            self.current_hotkey = hotkey_str
        except Exception as e:
            logger.error(f"Failed to set hotkey '{hotkey_str}': {e}")

    def load_model(self, size="base", device="cuda", compute_type="float16"):
        """Faster-Whisperモデルをロードする"""
        if self.model is None or self.model_size != size:
            logger.info(f"Loading Whisper Model: {size} on {device}...")
            try:
                self.model = WhisperModel(size, device=device, compute_type=compute_type)
                self.model_size = size
                self.device = device
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                # Fallback to CPU if CUDA fails
                if device == "cuda":
                    logger.warning("Falling back to CPU...")
                    self.load_model(size, "cpu", "int8")

    def get_input_devices(self):
        """利用可能なマイクデバイスのリストを返す"""
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        devices = []
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = self.p.get_device_info_by_host_api_device_index(0, i).get('name')
                devices.append({"id": i, "name": name})
        return devices

    def start_recording(self, device_index=None):
        """録音を開始する (非同期)"""
        if self.is_recording:
            return
        self.frames = []
        self.is_recording = True
        
        def _record():
            try:
                stream = self.p.open(format=self.format,
                                     channels=self.channels,
                                     rate=self.rate,
                                     input=True,
                                     input_device_index=device_index,
                                     frames_per_buffer=self.chunk)
                
                logger.info("Recording started...")
                while self.is_recording:
                    data = stream.read(self.chunk)
                    self.frames.append(data)
                
                stream.stop_stream()
                stream.close()
                logger.info("Recording stopped.")
            except Exception as e:
                logger.error(f"Recording Error: {e}")
                self.is_recording = False
        self.record_thread = threading.Thread(target=_record)
        self.record_thread.start()

    def stop_recording(self):
        """録音を停止し、テキスト変換を行う"""
        if not self.is_recording:
            return None
        self.is_recording = False
        if self.record_thread:
            self.record_thread.join()
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            wf = wave.open(temp_wav.name, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            temp_path = temp_wav.name
        
        # 認識実行
        return self.transcribe(temp_path)

    def transcribe(self, audio_path):
        """音声ファイルをテキストに変換する"""
        if not self.model:
            # 初回または設定変更時にロード
            self.load_model()
        
        if not self.model:
            return "Error: Model not loaded."
        logger.info("Transcribing...")
        start_ts = time.time()
        
        try:
            # 言語を日本語(ja)に固定し、initial_promptで文脈を与えることで精度向上
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language="ja",
                initial_prompt="こんにちは。これはチャットAIへの音声入力です。"
            )
            text = " ".join([segment.text for segment in segments]).strip()
            
            duration = time.time() - start_ts
            logger.info(f"Transcribed in {duration:.2f}s: {text}")
            
            # 一時ファイル削除
            try:
                os.remove(audio_path)
            except:
                pass
                
            return text
        except Exception as e:
            logger.error(f"Transcription Error: {e}")
            return ""

# シングルトンインスタンス作成
voice_input_manager = VoiceInputManager()
