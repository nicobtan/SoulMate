import os
import time
import logging
import threading
import gc  # Added for memory management
import tempfile
import wave
import torch
import pyaudio
import webrtcvad
import numpy as np
from faster_whisper import WhisperModel

# --- Monkey Patch for Torchaudio > 2.1 vs SpeechBrain ---
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    # Mocking the removed function to prevent SpeechBrain crash
    torchaudio.list_audio_backends = lambda: ["soundfile"]
# --------------------------------------------------------

# from speechbrain.inference.foreign_class import ForeignClass
from .onnx_emotion_recognizer import OnnxEmotionRecognizer


# Logger
logger = logging.getLogger(__name__)

class SoulMateEars:
    """
    High-End Hearing Module for SoulMate.
    Integrates Faster-Whisper (ASR) and SpeechBrain (SER).
    """

    def __init__(self, stt_model_size="large-v2", device="cuda"):
        self.device = device
        self.stt_model_size = stt_model_size
        self._is_listening = False
        
        # Audio Config
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000 # Required for both Whisper and VAD
        self.CHUNK = 320 # 20ms frame for VAD (16000 * 0.02)
        
        # VAD
        self.vad = webrtcvad.Vad(2) # Mode 2: Aggressive enough but balanced
        self.p = pyaudio.PyAudio()

        logger.info("🎧 [SoulMateEars] Initializing High-End Ears (Stable Mode)...")
        self._log_vram("Pre-Init")
        
        # 1. Load STT (Faster-Whisper) with Fallback
        try:
            logger.info(f"🎧 Loading Whisper ({stt_model_size}) on {device}...")
            
            # Strategy: Robust Fallback Chain (The "Unbreakable" Chain)
            # 1. Large-v2 + int8_float16 (Best VRAM/Perf)
            # 2. Large-v2 + float16 (Standard, guaranteed to work)
            # 3. Medium + float16 (Emergency Backup)
            
            candidates = [
                ("large-v2", "int8_float16"),
                ("large-v2", "float16"),
                ("medium", "float16")
            ]
            
            # If standard int8/float16 strategy fails, we loop through explicitly
            for model_name, compute_type_candidate in candidates:
                try:
                    logger.info(f"🎧 Attempting to load Whisper '{model_name}' with '{compute_type_candidate}'...")
                    
                    self.stt_model = WhisperModel(model_name, device=device, compute_type=compute_type_candidate)
                    
                    # Update active settings if successful
                    self.stt_model_size = model_name 
                    logger.info(f"✅ [SoulMateEars] Whisper Loaded successfully: {model_name} ({compute_type_candidate})")
                    self._log_vram(f"Post-Load-{compute_type_candidate}")
                    break
                    
                except Exception as load_err:
                    logger.warning(f"⚠️ Failed with {model_name}/{compute_type_candidate}: {load_err}")
                    if (model_name, compute_type_candidate) == candidates[-1]:
                        logger.error("❌ All Whisper load attempts failed. Ears are deaf.")
                        raise load_err # Give up if even Medium fails
            
        except Exception as e:
            logger.error(f"❌ Whisper Load Failed: {e}")
            raise e

        # 2. Load SER (ONNX Optimized)
        try:
            logger.info("🎧 Loading Emotion Model (ONNX Int8)...")
            self.emotion_classifier = OnnxEmotionRecognizer(device=device)
            if not self.emotion_classifier.session:
                 logger.warning("⚠️ ONNX Model failed to load (Session is None). Emotion detection disabled.")
                 self.emotion_classifier = None
            else:
                 logger.info("✅ Emotion Model Loaded (ONNX).")

        except Exception as e:
            logger.error(f"❌ Emotion Model Load Failed: {e}")
            self.emotion_classifier = None

        # Final Cleanup
        gc.collect()
        torch.cuda.empty_cache()
        self._log_vram("Init-Complete")

    def _log_vram(self, label=""):
        if self.device == "cuda" and torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            logger.debug(f"💾 VRAM [{label}]: Alloc={allocated:.2f}GB, Rsrv={reserved:.2f}GB")




    def listen_and_process(self, timeout=None):
        """
        Listens to microphone, detects speech via VAD, records, and processes.
        Returns: {"text": str, "emotion": str, "confidence": float}
        """
        audio_data = self._record_vad(timeout=timeout)
        if not audio_data:
            return None
            
        return self.process_audio(audio_data)

    def process_audio(self, audio_bytes):
        """
        Process raw audio bytes (16kHz, Mono, PCM16).
        """
        # Save to temp file strictly for models that require file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            wf = wave.open(tmp.name, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(audio_bytes)
            wf.close()
            tmp_path = tmp.name

        try:
            # 1. Faster-Whisper
            text = self._transcribe(tmp_path)
            
            # 2. Emotion Recognition (ONNX)
            emotion = "neutral"
            confidence = 0.0
            if self.emotion_classifier and text: # Only check emotion if there is speech
                 # Pass raw bytes directly to ONNX (saves I/O)
                 emotion, confidence = self._analyze_emotion(audio_bytes)
            
            return {
                "text": text,
                "emotion": emotion,
                "confidence": confidence,
                "audio_path": tmp_path # Keep file for playback/debugging?
            }
            
            
        finally:
            # Memory Cleanup
            gc.collect()
            torch.cuda.empty_cache()
            self._log_vram("Post-Process-GC")

            # Clean up temp file? Or keep it? 
            # For now, we delete it to save space, but maybe user wants it.
            # Let's delete it.
            try:
                os.remove(tmp_path)
            except:
                pass

    def _transcribe(self, audio_path):
        segments, info = self.stt_model.transcribe(
            audio_path,
            beam_size=5,
            best_of=5, # Optimization: Check more candidates
            patience=1.0, # Increased patience for better accuracy
            language="ja",
            task="transcribe", # Explicitly define task
            initial_prompt="聞こえますか？はい、聞こえます。日本語で話しましょう。マイクのテストです。", # Hypnotic Context
            condition_on_previous_text=False, 
            vad_filter=True 
        )
        
        # Log detection stats for verification
        if info:
             logger.info(f"🎤 [Whisper] Language: {info.language} ({info.language_probability:.0%}) | Duration: {info.duration:.2f}s")
        
        text = " ".join([s.text for s in segments]).strip()
        
        # --- HALLUCINATION FILTER ---
        # Whisper often hallucinates these specific phrases on silence/noise.
        # We ignore them to prevent "English Ghost" spam.
        hallucinations = [
            "Can you?", "Thank you.", "You", "Amara", "Bye.", 
            "I can you...", "Thank you for watching."
        ]
        
        # Check for exact matches or very short garbage
        if text in hallucinations:
            logger.warning(f"🚫 [Whisper] Hallucination Filtered: '{text}'")
            return ""
            
        # Check startswith for variations like "Thank you very much"
        if any(text.lower().startswith(h.lower()) for h in ["Thank you", "Can you", "Amara"]):
             logger.warning(f"🚫 [Whisper] Hallucination Filtered (Prefix): '{text}'")
             return ""
        # ----------------------------

        return text

    def _analyze_emotion(self, audio_data):
        """
        Returns (emotion_label, confidence_score)
        Input: audio_data (bytes or path, but ONNX helper handles bytes best)
        """
        try:
            # Use OnnxEmotionRecognizer
            label, confidence = self.emotion_classifier.predict(audio_data)
            
            # Map labels to SoulMate standard
            # ONNX Model: neutral, anger, happy, sad
            # SoulMate Target: neutral, anger, happy, sadness
            label_map = {
                "sad": "sadness"
            }
            return label_map.get(label, label), confidence
            
        except Exception as e:
            logger.error(f"Emotion Analysis Error: {e}")
            return "neutral", 0.0

    def _record_vad(self, timeout=None):
        """
        Records audio using VAD to detect speech start/end.
        """
        stream = self.p.open(format=self.FORMAT,
                             channels=self.CHANNELS,
                             rate=self.RATE,
                             input=True,
                             frames_per_buffer=self.CHUNK)

        frames = []
        speech_frames = []
        
        is_speech = False
        silence_duration = 0
        MAX_SILENCE = 1.0 # Stop after 1s silence
        MIN_SPEECH = 0.5 # Minimum speech duration to process
        
        logger.debug("🎤 Listening...")
        
        start_time = time.time()
        
        try:
            while True:
                # BREAK CONDITION 1: Timeout (only if not speaking)
                if not is_speech and timeout and (time.time() - start_time > timeout):
                    # logger.debug("VAD Timeout (No speech detected)")
                    break
                    
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                # frames.append(data) # Unused
                
                # Check VAD
                # VAD requires raw PCM bytes
                try:
                    is_active = self.vad.is_speech(data, self.RATE)
                except:
                    is_active = False

                if is_active:
                    if not is_speech:
                        logger.debug("🗣️ Speech Detected")
                        is_speech = True
                    speech_frames.append(data)
                    silence_duration = 0
                else:
                    if is_speech:
                        speech_frames.append(data) # Add tail silence
                        silence_duration += (self.CHUNK / self.RATE)
                        if silence_duration > MAX_SILENCE:
                            logger.debug("End of Speech")
                            break
                    else:
                        # Pre-buffer logic could go here
                        pass

        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()

        if not speech_frames:
            return None
            
        total_duration = len(speech_frames) * (self.CHUNK / self.RATE)
        if total_duration < MIN_SPEECH:
            return None # Implementation noise
            
        return b''.join(speech_frames)

    def close(self):
        """Releases PyAudio resources."""
        if hasattr(self, 'p') and self.p:
            try:
                self.p.terminate()
                logger.info("🎧 [SoulMateEars] PyAudio terminated.")
            except Exception as e:
                logger.error(f"🎧 [SoulMateEars] PyAudio termination failed: {e}")
                
if __name__ == "__main__":
    # Simple Test
    ears = SoulMateEars()
    try:
        while True:
            res = ears.listen_and_process()
            if res:
                print(f"📝 {res['text']} [{res['emotion']}]")
    except KeyboardInterrupt:
        ears.close()
