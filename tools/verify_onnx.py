import onnxruntime as ort
import numpy as np

def verify():
    path = "models/emotion_model/emotion.clean.onnx"
    try:
        sess = ort.InferenceSession(path, providers=['CPUExecutionProvider'])
        inp_name = sess.get_inputs()[0].name
        out_name = sess.get_outputs()[0].name
        
        test_wav = np.random.randn(1, 32000).astype(np.float32)
        out = sess.run([out_name], {inp_name: test_wav})[0]
        print(f"[OK] Inference works! Output: {out.shape}")
        print(out)
    except Exception as e:
        print(f"[FAIL] Inference crashed: {e}")

if __name__ == "__main__":
    verify()
