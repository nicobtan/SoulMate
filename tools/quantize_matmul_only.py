import os
from onnxruntime.quantization import quantize_dynamic, QuantType
import onnxruntime as ort
import numpy as np

def run_specific_quantization():
    input_model = "models/emotion_model/emotion.clean.onnx"
    output_model = "models/emotion_model/emotion.quant.onnx"
    
    print(f"[INFO] Quantizing {input_model} (MatMul Only)...")
    
    try:
        quantize_dynamic(
            input_model,
            output_model,
            weight_type=QuantType.QUInt8,
            op_types_to_quantize=['MatMul', 'Gemm'] # Focus on heavy ops
        )
        print(f"[OK] Quantized model saved to {output_model}")
        
        # Verify
        print("[INFO] Verifying...")
        sess = ort.InferenceSession(output_model, providers=['CPUExecutionProvider'])
        test_wav = np.random.randn(1, 32000).astype(np.float32)
        inp_name = sess.get_inputs()[0].name
        out_name = sess.get_outputs()[0].name
        
        out = sess.run([out_name], {inp_name: test_wav})[0]
        print(f"[OK] Inference Successful. Output Shape: {out.shape}")
        
    except Exception as e:
        print(f"[FAIL] Quantization failed: {e}")

if __name__ == "__main__":
    run_specific_quantization()
