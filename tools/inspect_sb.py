import sys
import os
import torchaudio
# Monkey patch for Torchaudio > 2.1 vs SpeechBrain
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

import speechbrain
print(f"SpeechBrain Version: {speechbrain.__version__ if hasattr(speechbrain, '__version__') else 'Unknown'}")

try:
    import speechbrain.inference.interfaces as interfaces
    print("\n--- interfaces attributes ---")
    print(dir(interfaces))
    
    if hasattr(interfaces, 'foreign_class'):
        print("\n--- interfaces.foreign_class attributes ---")
        print(dir(interfaces.foreign_class))
except Exception as e:
    print(f"Error inspecting interfaces: {e}")

try:
    from speechbrain.inference.classifiers import EncoderClassifier
    print("\nSUCCESS: EncoderClassifier found in speechbrain.inference.classifiers")
except Exception as e:
    print(f"FAILED: EncoderClassifier import: {e}")

