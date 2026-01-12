import os
import logging
import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)

class OnnxEmotionRecognizer:
    def __init__(self, model_path="models/emotion_model/emotion.quant.onnx", device="gpu"):
        self.model_path = model_path
        self.device = device
        self.session = None
        self.labels = ["neutral", "anger", "happy", "sad"] # Standard IEMOCAP mapping
        
        self._load_model()
        
    def _load_model(self):
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"ONNX Model not found at {self.model_path}")
                
            providers = ['CPUExecutionProvider']
            if self.device == "gpu" or self.device == "cuda":
                # Prioritize CUDA if available
                # 'CUDAExecutionProvider' requires cuDNN/CUDA libs.
                # If fails, falls back to CPU automatically usually, but specifying explicit list is better.
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            logger.info(f"🧠 Loading ONNX Emotion Model from {self.model_path}...")
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            logger.info(f"✅ ONNX Model Loaded (Providers: {self.session.get_providers()})")
            
        except Exception as e:
            logger.error(f"❌ Failed to load ONNX model: {e}")
            self.session = None

    def predict(self, audio_data):
        """
        Predict emotion from raw audio bytes or numpy array.
        Input: 
            audio_data: bytes (PCM16) or np.array (float32)
        Returns:
            (emotion_label, confidence_score)
        """
        if self.session is None:
            return "neutral", 0.0
            
        try:
            # Preprocess
            input_tensor = self._preprocess(audio_data)
            
            # Inference
            inputs = {self.session.get_inputs()[0].name: input_tensor}
            outputs = self.session.run(None, inputs)
            
            # Output is [1, 4] probabilities (Softmaxed in export)
            probs = outputs[0][0]
            
            # Get Max
            idx = np.argmax(probs)
            confidence = float(probs[idx])
            label = self.labels[idx]
            
            return label, confidence
            
        except Exception as e:
            logger.error(f"ONNX Inference Error: {e}")
            return "neutral", 0.0

    def _preprocess(self, audio_data):
        """
        Convert audio bytes/array to input tensor format.
        Target: [1, Time] float32 array.
        """
        # If bytes (PCM16)
        if isinstance(audio_data, bytes):
            # Convert to numpy int16 -> float32
            data = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            # Normalize to [-1, 1] usually required if model trained on float audio
            # Wav2Vec2 usually works on scale of raw audio values if they are similar to training.
            # Torchaudio load usually returns [-1, 1].
            # PCM16 is [-32768, 32767]. We should normalize.
            data = data / 32768.0
        
        elif isinstance(audio_data, np.ndarray):
            data = audio_data.astype(np.float32)
        else:
            raise ValueError("Unsupported audio format")
            
        # Add Batch Dimension [1, Time]
        if data.ndim == 1:
            data = data[np.newaxis, :]
            
        return data

if __name__ == "__main__":
    # Internal test
    rec = OnnxEmotionRecognizer()
    if rec.session:
        # Dummy audio
        dummy = np.random.randn(1, 16000).astype(np.float32)
        l, c = rec.predict(dummy)
        print(f"Test Prediction: {l} ({c:.2f})")
