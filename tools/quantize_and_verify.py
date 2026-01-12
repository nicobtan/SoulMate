import os
import torch
import onnx
import onnxruntime as ort
import numpy as np
from onnxruntime.quantization import quantize_dynamic, QuantType

def run_quantization():
    input_model_path = "models/emotion_model/emotion.clean.onnx"
    output_model_path = "models/emotion_model/emotion.quant.onnx"
    
    if not os.path.exists(input_model_path):
        print(f"[FAIL] Input model {input_model_path} not found.")
        return

    print(f"[INFO] Quantizing {input_model_path} to Int8...")
    
    # Quantize
    quantize_dynamic(
        input_model_path,
        output_model_path,
        weight_type=QuantType.QUInt8
    )
    print(f"[OK] Quantized model saved to {output_model_path}")
    
    # Verify
    print("[INFO] Verifying Model Inference...")
    try:
        ort_sess = ort.InferenceSession(output_model_path, providers=['CPUExecutionProvider'])
        
        # Test Input [Batch, Time] -> [1, 32000]
        test_wav = np.random.randn(1, 32000).astype(np.float32)
        
        # Run
        # Note: We must know input name. Since we removed explicit naming in last attempt,
        # we must inspect the input name from the session.
        input_name = ort_sess.get_inputs()[0].name
        output_name = ort_sess.get_outputs()[0].name
        print(f"[INFO] ONNX Input Name: {input_name}")
        print(f"[INFO] ONNX Output Name: {output_name}")
        
        out = ort_sess.run([output_name], {input_name: test_wav})[0]
        print(f"[OK] Inference Successful. Output Shape: {out.shape}")
        print(f"[INFO] Output Sample: {out}")
        
    except Exception as e:
        print(f"[FAIL] Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_quantization()
