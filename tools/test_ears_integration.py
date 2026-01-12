import sys
import os
import numpy as np
import logging

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.voice.soulmate_ears import SoulMateEars

# Configure Logging
logging.basicConfig(level=logging.INFO)

def test_integration():
    print("Testing SoulMateEars Integration...")
    
    # 1. Initialize
    try:
        ears = SoulMateEars(device="cpu") # Use CPU to be safe/fast for test
    except Exception as e:
        print(f"[FAIL] Init Failed: {e}")
        return

    # 2. Create Dummy Audio (1 sec sine wave 440Hz)
    # 16kHz, Mono, PCM16
    rate = 16000
    duration = 2.0 # 2 seconds
    t = np.linspace(0, duration, int(rate * duration), endpoint=False)
    # Generate pure tone which Whisper might ignore or transcribe as ???
    # Int16 range
    data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    audio_bytes = data.tobytes()
    
    print(f"Generated Audio: {len(audio_bytes)} bytes")
    
    # 3. Process
    try:
        # Note: Whisper might fail to detect language on pure tone, but shouldn't crash.
        result = ears.process_audio(audio_bytes)
        print("Result:", result)
        
        if result['emotion'] in ["neutral", "happy", "anger", "sadness"]:
            print("[OK] Emotion Detected:", result['emotion'])
            print("[OK] Confidence:", result['confidence'])
        else:
            print("[WARN] Unexpected emotion label:", result['emotion'])
            
    except Exception as e:
        print(f"[FAIL] Process Audio Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()
