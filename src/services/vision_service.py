import torch
from PIL import Image
from transformers import AutoProcessor, PaliGemmaForConditionalGeneration
import threading
import logging

logger = logging.getLogger(__name__)

class VisionService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VisionService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # Configuration
        self.model_id = "google/paligemma-3b-mix-224" 
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        # Fallback tracking
        self.fallback_cpu_triggered = False

        self.model = None
        self.processor = None
        self.is_loading = False
        self._initialized = True
        self.log_callback = None # Callback for frontend logging

    def set_log_callback(self, callback):
        self.log_callback = callback

    def _send_log(self, message, type='info'):
        if self.log_callback:
            self.log_callback(message, type=type)

    def load_model(self):
        """Loads the model (Heavy operation, done on first access)"""
        if self.model is not None:
            return

        self.is_loading = True
        logger.info(f"👁️ [Vision] Loading PaliGemma model on {self.device} ({self.dtype})...")
        
        try:
            self.processor = AutoProcessor.from_pretrained(self.model_id)
            self.model = PaliGemmaForConditionalGeneration.from_pretrained(
                self.model_id,
                torch_dtype=self.dtype,
                device_map=self.device,
                revision="bfloat16", 
            ).eval()
            
            
            logger.info("👁️ [Vision] Model Loaded Successfully!")
            device_msg = f"🔮 [System] Current Device: {self.model.device}"
            logger.info(device_msg)
            self._send_log(device_msg, type='info') 
        except Exception as e:
            logger.error(f"👁️ [Vision] Load Failed on {self.device}: {e}")
            
            if self.device == "cuda":
                logger.warning("⚠️ [Vision] Falling back to CPU...")
                self.device = "cpu"
                self.dtype = torch.float32
                self.fallback_cpu_triggered = True
                
                # Retry Load on CPU
                try:
                    self.model = PaliGemmaForConditionalGeneration.from_pretrained(
                        self.model_id,
                        torch_dtype=self.dtype,
                        device_map=self.device,
                        revision="bfloat16", 
                    ).eval()
                    logger.info("👁️ [Vision] Fallback to CPU Successful!")
                except Exception as e2:
                    logger.error(f"👁️ [Vision] CPU Fallback Failed: {e2}")
                    raise e2
            else:
                raise e
        finally:
            self.is_loading = False

    def analyze_image(self, image: Image.Image, prompt: str = "caption en"):
        """Analyzes image and returns caption (English)"""
        if self.model is None:
            self.load_model()

        logger.info(f"👁️ [Vision] Analyzing image... (Prompt: {prompt})")
        
        try:
            # Preprocessing
            # Note: PaliGemma expects specific input formatting handled by processor
            model_inputs = self.processor(text=prompt, images=image, return_tensors="pt").to(self.device)
            input_len = model_inputs["input_ids"].shape[-1]

            # Inference (Slow on CPU)
            with torch.inference_mode():
                generation = self.model.generate(
                    **model_inputs, 
                    max_new_tokens=100, 
                    do_sample=False
                )
                generation = generation[0][input_len:]
                decoded = self.processor.decode(generation, skip_special_tokens=True)
                
            # Retry with fallback prompt if unanswerable
            if "unanswerable" in decoded.lower() and prompt == "caption en":
                logger.warning("👁️ [Vision] Result 'unanswerable'. Retrying with 'describe'...")
                return self.analyze_image(image, prompt="describe the details")
                
            logger.info(f"👁️ [Vision] Result: {decoded}")
            return decoded

        except Exception as e:
            logger.error(f"👁️ [Vision] Inference Error: {e}")
            # Fallback or robust error handling could be added here
            return "Error parsing image"

# Singleton Instance
vision_service = VisionService()
