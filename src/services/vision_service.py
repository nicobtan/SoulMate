import os
import time
import logging
from PIL import Image
import threading
import io
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Google GenAI SDK
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# --- Robust Environment Loading (Absolute Path) ---
try:
    # src/services/vision_service.py -> src/services -> src -> root -> .env
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # Fallback to default
        load_dotenv()
except Exception:
    pass
# --------------------------------------------------

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
        self.model_name = "gemini-2.5-flash-lite" 
        self.client = None
        
        # 1. Try to get key from environment (Explicit Loading)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        self._initialized = True
        self.log_callback = None
        
        # Debug Logging (Critical) as requested
        found_status = 'Found' if self.api_key else 'Missing'
        path_str = str(env_path) if 'env_path' in globals() else "Unknown"
        logger.info(f"🔑 [Vision] API Key Status: {found_status} (Path: {path_str})")

        # Attempt auto-initialization if key exists
        if self.api_key:
            self.configure(self.api_key)
        else:
            logger.error("❌ [Vision] API Key not found in environment. Please check .env file.")

    def set_log_callback(self, callback):
        self.log_callback = callback

    def _log(self, message, type='vision'):
        if self.log_callback:
            self.log_callback(message, type=type)
        logger.info(message)

    def configure(self, api_key):
        """Called by ConfigManager or Main to set API Key manually."""
        if not api_key:
            return
            
        self.api_key = api_key
        try:
            self.client = genai.Client(api_key=self.api_key)
            self._log(f"👁️ [Vision] Client Initialized ({self.model_name})")
        except Exception as e:
            logger.error(f"Vision Client Init Error: {e}")
            self._log(f"❌ [Vision] Client Init Failed: {e}", 'error')

    def analyze_image(self, image: Image.Image, prompt: str = ""):
        """
        Analyzes the image using Gemini 2.5 Flash Lite.
        """
        # Guard Clause: Client Logic
        if not self.client:
            # Try lazy init one last time
            if self.api_key:
                 self.configure(self.api_key)
            
            if not self.client:
                 msg = "Vision API Client not ready (No API Key or Init Failed)."
                 logger.error(msg)
                 return msg

        try:
            # --- Debug: Save Image to Disk ---
            try:
                import datetime
                debug_dir = os.path.join(os.getcwd(), 'dist', 'debug')
                history_dir = os.path.join(debug_dir, 'history')
                os.makedirs(history_dir, exist_ok=True)
                
                # Save Latest
                latest_path = os.path.join(debug_dir, 'latest_vision.jpg')
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(latest_path, quality=85)
                
                # Save History
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                history_path = os.path.join(history_dir, f"{timestamp}.jpg")
                image.save(history_path, quality=85)
                
                self._log(f"📸 [Vision] Image captured: {timestamp}")
            except Exception as e:
                logger.error(f"Failed to save debug image: {e}")
            # ---------------------------------

            window_title = prompt if prompt else "Unknown Window"
            self._log(f"👁️ [Vision] Analyzing '{window_title}'...")

            # Convert PIL Image to Bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            # Construct Prompt
            system_instruction = """
You are the visual cortex of 'SoulMate', an AI desktop partner.
Your task is to analyze the user's screen and describe it for the conversational AI.
Output MUST be in Japanese.
"""
            user_prompt = f"""
ユーザーはPCで '{window_title}' というウィンドウを見ています。
この画面の状況（ゲームならその内容や戦況、作業なら進捗など）を視覚的に解説し、
パートナーとして話しかけるための短いコメント（感想やツッコミ）を出力してください。
返答は日本語で、"Yes/No"ではなく具体的な内容を含めてください。
GAMEPLAY NOTE: If this is a game, explain what is happening in the game scene.
"""

            start_time = time.time()
            
            # API Call
            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[image_part, user_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=300
                )
            )
            elapsed = time.time() - start_time

            result_text = response.text.strip() if response.text else "No response"
            
            # Logging
            log_text = result_text.replace('\n', ' ')
            if len(log_text) > 100: log_text = log_text[:100] + "..."
            
            self._log(f"👁️ [Vision] Result ({elapsed:.2f}s): {log_text}")
            return result_text

        except Exception as e:
            logger.error(f"Analysis Error: {e}")
            self._log(f"❌ [Vision] Error: {e}", 'error')
            traceback.print_exc()
            return f"Error: {str(e)}"

# Singleton Instance
vision_service = VisionService()

