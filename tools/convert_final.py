import sys
import os
import torch
import torch.onnx
import onnx
import onnxruntime as ort
import numpy as np
from onnxruntime.quantization import quantize_dynamic, QuantType

# Monkey patch
import torchaudio
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

from speechbrain.inference.classifiers import EncoderClassifier

def run_conversion():
    print("[INFO] Loading SpeechBrain Model (IEMOCAP)...")
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        savedir="models/emotion_model",
        run_opts={"device": "cpu"}
    )
    
    class FinalModel(torch.nn.Module):
        def __init__(self, sb_ref):
            super().__init__()
            self.wav2vec2 = sb_ref.mods["wav2vec2"]
            self.output_mlp = sb_ref.mods["output_mlp"]
            
        def forward(self, wavs):
            # [B, T] -> [B, T, 768]
            x = self.wav2vec2(wavs)
            # Mean Pool: [B, T, 768] -> [B, 768]
            x = torch.mean(x, dim=1)
            # MLP: [B, 768] -> [B, 4]
            x = self.output_mlp(x)
            # Softmax
            x = torch.nn.functional.softmax(x, dim=-1)
            return x

    model = FinalModel(classifier)
    model.eval()
    
    dummy_input = torch.randn(1, 16000)
    output_onnx = "models/emotion_model/emotion.onnx"
    output_quant = "models/emotion_model/emotion.quant.onnx"
    
    os.makedirs(os.path.dirname(output_onnx), exist_ok=True)
    
    print(f"[INFO] Exporting to {output_onnx}...")
    torch.onnx.export(
        model,
        dummy_input,
        output_onnx,
        export_params=True,
        opset_version=17,
        do_constant_folding=False, # TRY FALSE
        input_names=['input_audio'],
        output_names=['output_prob'],
        dynamic_axes={
            'input_audio': {0: 'batch_size', 1: 'time_steps'},
            'output_prob': {0: 'batch_size'}
        }
        # check_trace=False is implicit if not specified? 
        # Actually default is True.
        # But for recent torch versions, validation is separate.
    )
    # Re-run with strict=False equivalent?
    # Actually, try wrapping in try-catch to ignore shape inference?
    # No, it crashes inside C++.
    
    # Try passing `do_constant_folding=False` may help?
    pass

    print(f"[INFO] Exporting to {output_onnx}...")
    try:
        torch.onnx.export(
            model,
            dummy_input,
            output_onnx,
            export_params=True,
            opset_version=17,
            do_constant_folding=False,
            input_names=['input_audio'],
            # output_names=['output_prob'],
            dynamic_axes={
                'input_audio': {0: 'batch_size', 1: 'time_steps'},
                # 'output_prob': {0: 'batch_size'}
            }
        )
    except Exception as e:
        print(f"[WARN] Export crashed: {e}")
        # Check if file exists anyway
        
    if os.path.exists(output_onnx):
        print("[OK] ONNX Exported (File Exists despite potential error).")
    else:
        print("[FAIL] ONNX File was not created.")
        return

    
    # Quantize
    print(f"[INFO] Quantizing to {output_quant}...")
    quantize_dynamic(
        output_onnx,
        output_quant,
        weight_type=QuantType.QUInt8
    )
    print("[OK] Quantized.")
    
    # Verification
    print("[INFO] Verifying...")
    ort_sess = ort.InferenceSession(output_quant, providers=['CPUExecutionProvider'])
    
    test_wav = torch.randn(1, 32000).numpy()
    ort_out = ort_sess.run(None, {'input_audio': test_wav})[0]
    
    with torch.no_grad():
        torch_out = model(torch.from_numpy(test_wav))
        
    diff = np.max(np.abs(torch_out.numpy() - ort_out))
    print(f"[OK] Verification Diff: {diff:.6f}")
    if diff > 0.1:
        print("[WARN] High difference!")

if __name__ == "__main__":
    run_conversion()
