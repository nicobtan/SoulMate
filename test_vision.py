import torch
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration, BitsAndBytesConfig
from PIL import Image
import os
import sys

def main():
    # 1. Initial Setup
    print("Initializing PaliGemma Test...")
    
    image_path = "test.jpg"
    if not os.path.exists(image_path):
        print(f"\n[ERROR] '{image_path}' not found.")
        print("Please place a test image named 'test.jpg' in this directory.")
        return

    model_id = "google/paligemma-3b-mix-224"
    
    # 3. Load Model (Force CPU for RTX 50 Series / sm_120 Compatibility)
    print(f"Loading Model: {model_id}...")
    
    # RTX 50 Series Workaround: Force CPU as current PyTorch wheels lack sm_120 kernels
    device = "cpu"
    print(f"Device: {device} (Forced due to RTX 50 Series compatibility issue)")

    try:
        if device == "cuda":
             pass # Unreachable for now
        else:
            print("Mode: Float32 (CPU)")
            print("Note: Local Vision L1 will run on CPU. Expect slower inference (~seconds).")
            model = PaliGemmaForConditionalGeneration.from_pretrained(
                model_id,
                device_map="cpu",
                torch_dtype=torch.float32 
            )

        processor = AutoProcessor.from_pretrained(model_id)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # 4. Process Image
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Failed to open image: {e}")
        return

    # 5. Inference
    prompt = "describe this image in Japanese"
    print(f"Input Prompt: {prompt}")
    print("Running Inference...")

    try:
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(model.device)
        input_len = inputs["input_ids"].shape[-1]

        with torch.inference_mode():
            generation = model.generate(
                **inputs, 
                max_new_tokens=100, 
                do_sample=False
            )
            # Slice output to remove prompt
            generation = generation[0][input_len:]
            decoded = processor.decode(generation, skip_special_tokens=True)

        print("\n" + "="*30)
        print(f"RESULT: {decoded}")
        print("="*30 + "\n")

    except Exception as e:
        print(f"Inference Error: {e}")

if __name__ == "__main__":
    main()
