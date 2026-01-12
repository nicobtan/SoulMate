import onnx

def sanitize():
    path = "models/emotion_model/emotion.onnx"
    out_path = "models/emotion_model/emotion.clean.onnx"
    
    print(f"Loading {path}...")
    model = onnx.load(path)
    
    print("Stripping value_info (shape info)...")
    del model.graph.value_info[:]
    # Also optionally clear output shapes if they are wrong?
    # But output shapes are in graph.output
    # let's keep graph.output for now, usually intermediate shapes cause the issue.
    
    # We can also run shape inference to RE-populate with correct shapes if ONNX runtime can deduce them better than PyTorch exporter?
    # from onnx import shape_inference
    # model = shape_inference.infer_shapes(model)
    # But if infer_shapes is what crashes, we should NOT run it.
    
    print(f"Saving to {out_path}...")
    onnx.save(model, out_path)
    print("Done.")

if __name__ == "__main__":
    sanitize()
