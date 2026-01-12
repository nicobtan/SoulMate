import sys
import os
import torch
import numpy as np

# Monkey patch for SpeechBrain
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

try:
    from speechbrain.inference.classifiers import EncoderClassifier as ForeignClass
    print("Code [OK] Imports")
except ImportError:
    print("Code [FAIL] Imports")
    sys.exit(1)

def run():
    print("Code [INFO] Loading...")
    classifier = ForeignClass.from_hparams(
        source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        savedir="models/emotion_model",
        run_opts={"device": "cpu"}
    )
    
    print(f"Code [INFO] Keys: {classifier.mods.keys()}")
    
    # Trace logic manually
    wav2vec2 = classifier.mods["wav2vec2"]
    output_mlp = classifier.mods["output_mlp"]
    
    dummy = torch.randn(1, 16000)
    
    print("Code [INFO] Running Wav2Vec2...")
    out = wav2vec2(dummy)
    print(f"Code [INFO] Wav2Vec2 Out: {out.shape}")
    
    print("Code [INFO] Running Mean Pool...")
    out = torch.mean(out, dim=1)
    print(f"Code [INFO] Pool Out: {out.shape}")
    
    print("Code [INFO] Running MLP...")
    out = output_mlp(out)
    print(f"Code [INFO] MLP Out: {out.shape}")
    
    print("Code [OK] Finished.")

if __name__ == "__main__":
    run()
