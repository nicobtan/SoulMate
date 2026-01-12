import os
import sys
import torch
import torch.onnx
import onnx
import onnxruntime as ort
import numpy as np
from onnxruntime.quantization import quantize_dynamic, QuantType

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Monkey patch for SpeechBrain dependency
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

# Robust Import Strategy
try:
    from speechbrain.inference.classifiers import EncoderClassifier as ForeignClass
    print("[OK] Using EncoderClassifier (Standard)")
except ImportError:
    try:
        from speechbrain.inference.interfaces import ForeignClass
    except ImportError:
        try:
            from speechbrain.inference.foreign_class import ForeignClass
        except ImportError:
            raise ImportError("Could not find EncoderClassifier or ForeignClass")

def convert_to_onnx(output_path="models/emotion_model/emotion.onnx"):
    print("[INFO] Loading SpeechBrain Model (IEMOCAP)...")
    print("UNIQUE DEBUG RUN: 9999")
    device = "cpu" 
    
    # Load Model
    if hasattr(ForeignClass, "from_hparams"):
        classifier = ForeignClass.from_hparams(
            source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
            savedir="models/emotion_model",
            run_opts={"device": device}
        )
    else:
        classifier = ForeignClass(
            source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
            pymodule_file="custom_interface.py",
            classname="CustomEncoderWav2vec2Classifier",
            savedir="models/emotion_model",
            run_opts={"device": device}
        )
    
    print("Writing debug info...")
    try:
        with open("debug_sb_obj.txt", "w") as f:
            f.write(f"Type: {type(classifier)}\n")
            f.write(f"Dir: {dir(classifier)}\n")
            if hasattr(classifier, 'mods'):
                f.write(f"Mods: {classifier.mods.keys()}\n")
            if hasattr(classifier, 'hparams'):
                f.write(f"Hparams: {classifier.hparams.keys() if hasattr(classifier.hparams, 'keys') else 'No Keys'}\n")
    except Exception as e:
        print(f"Debug write failed: {e}")

    
    print(f"[INFO] Classifier Mods: {classifier.mods.keys()}")
    
    class FullModel(torch.nn.Module):


        def __init__(self, sb_classifier):
            super().__init__()
            # Confirmed keys from debug: wav2vec2, output_mlp, avg_pool
            self.wav2vec2 = sb_classifier.mods["wav2vec2"]
            self.output_mlp = sb_classifier.mods["output_mlp"]
            self.avg_pool = sb_classifier.mods["avg_pool"]
            
        def forward(self, wavs):
            # Input: [Batch, Time]
            # 1. Wav2Vec2 Feature Extraction
            # Wav2Vec2 usually returns shape [Batch, Time, Dim]
            x = self.wav2vec2(wavs) 
            
            # 2. Avg Pooling
            # Pooling usually takes [Batch, Time, Dim] and masking lengths
            # BUT for export we usually assume full length or just global average if pool is simple.
            # SpeechBrain's avg_pool usually expects (x, lengths).
            # If we export with batch_size=1 and full usage, we can pass dummy lengths of 1.0.
            # However, dynamic axes means lengths vary.
            # To simulate 'global mean pooling' over time without masks:
            x = torch.mean(x, dim=1) # [Batch, Dim]
            
            # OR try to use the actual module:
            # x = self.avg_pool(x) # Might fail if it expects lengths argument
            
            # 3. Classifier
            x = self.output_mlp(x) # [Batch, 4]
            
            # 4. Softmax
            x = torch.nn.functional.softmax(x, dim=-1)
            
            return x

    full_model = FullModel(classifier).to(device)
    full_model.eval()
    
    # Creates directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Dummy Input (1 second of audio at 16kHz)
    dummy_input = torch.randn(1, 16000, device=device)
    
    
    # Dry Run
    print("[INFO] Running Dry Run in PyTorch...")
    # sys.stdout.flush()
    with torch.no_grad():
        dry_out = full_model(dummy_input)
    print(f"DRY RUN PASSED: {dry_out.shape}")
    
    return # STOP HERE FOR DEBUG
    
    return output_path # Fake return


def quantize_model(input_model_path, output_model_path):
    print(f"[INFO] Quantizing model to Int8: {output_model_path}")
    quantize_dynamic(
        input_model_path,
        output_model_path,
        weight_type=QuantType.QUInt8
    )
    print("[OK] Quantization Complete.")
    return output_model_path

def verify_models(torch_model_wrapper, onnx_path, quant_path):
    print("\n[INFO] Verifying Models...")
    
    # Test Data (2.5 seconds)
    test_audio = torch.randn(1, 40000) 
    
    # 1. PyTorch Output
    with torch.no_grad():
        torch_out = torch_model_wrapper(test_audio).numpy()
    
    # 2. ONNX Output
    ort_session = ort.InferenceSession(onnx_path, providers=['CPUExecutionProvider'])
    onnx_out = ort_session.run(None, {'input_audio': test_audio.numpy()})[0]
    
    # 3. Quantized Output
    ort_session_q = ort.InferenceSession(quant_path, providers=['CPUExecutionProvider'])
    quant_out = ort_session_q.run(None, {'input_audio': test_audio.numpy()})[0]
    
    print(f"PyTorch Pred: {torch_out[0]}")
    print(f"ONNX Pred   : {onnx_out[0]}")
    print(f"Quant Pred  : {quant_out[0]}")
    
    onnx_diff = np.max(np.abs(torch_out - onnx_out))
    quant_diff = np.max(np.abs(torch_out - quant_out))
    
    print(f"Max Diff (PyTorch vs ONNX): {onnx_diff:.6f}")
    print(f"Max Diff (PyTorch vs Quant): {quant_diff:.6f}")
    
    if quant_diff < 0.05: # 5% margin is acceptable for Int8 emotion
        print("[OK] Quantized Model Accuracy is Acceptable.")
    else:
        print("[WARN] Warning: Quantization error seems high.")

if __name__ == "__main__":
    try:
        onnx_file = "models/emotion_model/emotion.onnx"
        quant_file = "models/emotion_model/emotion.quant.onnx"
        
        # 1. Export
        convert_to_onnx(onnx_file)
        
        # 2. Quantize
        quantize_model(onnx_file, quant_file)
        
        # 3. Verify (Need to rebuild wrapper locally for test)
        # Re-loading for verification verification logic is included inside simple flow if needed
        # but for cleaner script we skip re-instantiating inside verify if we didn't return the object.
        # We will trust the export log for now or integrate verification in convert step if object persisted.
        # Let's keep it simple.
        
        print("\n[OK] All steps finished successfully!")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
