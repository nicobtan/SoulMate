import os
import time
import logging
from PIL import Image
import threading
import io
import traceback
from pathlib import Path
import json
from dotenv import load_dotenv

# Google GenAI SDK
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# --- Robust Environment Loading (Absolute Path) ---
try:
    # src/services/vision/vision_service.py -> src/services -> src -> root
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
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
        # Configuration
        self.model_name = "gemini-2.5-flash-lite" 
        self.client = None
        self.log_callback = None
        
        # Log suppression flags
        self._logged_capture = False
        self._logged_analyze = False
        self._logged_result = False
        
        # 1. Try to get key from environment (Explicit Loading)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
             # 2. Fallback: Try loading directly from settings/config.json
             try:
                 base_dir = os.path.dirname(os.path.abspath(__file__))
                 # Move up from src/services/vision -> settings
                 # 3 levels up: src/services/vision -> src/services -> src -> root
                 config_path = os.path.join(base_dir, "..", "..", "..", "settings", "config.json")
                 config_path = os.path.abspath(config_path)
                 
                 if os.path.exists(config_path):
                     with open(config_path, 'r', encoding='utf-8') as f:
                         data = json.load(f)
                         self.api_key = data.get('api_key')
                         if self.api_key:
                             logger.info(f"🔑 [Vision] API Key loaded from config.json fallback.")
             except Exception as e:
                 logger.error(f"Failed to load config.json fallback: {e}")

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

    def capture_screen(self):
        """Captures the target monitor and returns base64 string"""
        try:
            # Workspace Locking: Get Target Monitor Region
            target = self.monitor.get_target_monitor()
            region = None
            if target:
                region = (target.x, target.y, target.width, target.height)
                # logger.info(f"👁️ [Vision] Capturing Region: {region} (Monitor {target.name})") # Verbose off
            
            # Capture specific region
            screenshot = pyautogui.screenshot(region=region)
            
            # Resize if too large (Optimization)
            # Monitor 3 might be large, but we keep it reasonable for Vision API
            if screenshot.width > 1920:
                ratio = 1920 / screenshot.width
                new_h = int(screenshot.height * ratio)
                screenshot = screenshot.resize((1920, new_h), Image.Resampling.LANCZOS)

            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return img_str, screenshot.size
            
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None, (0, 0)

    def save_debug_image(self, image: Image.Image, prefix="latest_vision"):
        """Saves the image to dist/debug/ for inspection."""
        try:
            import datetime
            debug_dir = os.path.join(os.getcwd(), 'dist', 'debug')
            history_dir = os.path.join(debug_dir, 'history')
            os.makedirs(history_dir, exist_ok=True)
            
            # Save Latest
            latest_path = os.path.join(debug_dir, f'{prefix}.jpg')
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(latest_path, quality=85)
            
            # Save History
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = os.path.join(history_dir, f"{timestamp}_{prefix}.jpg")
            image.save(history_path, quality=85)
            
            if not self._logged_capture:
                self._log(f"📸 [Vision] Image captured: {timestamp} (Type: {prefix})")
                self._logged_capture = True
            return latest_path
        except Exception as e:
            logger.error(f"Failed to save debug image: {e}")
            return None

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
            self.save_debug_image(image, prefix="latest_vision")
            # ---------------------------------

            window_title = prompt if prompt else "Unknown Window"
            if not self._logged_analyze:
                self._log(f"👁️ [Vision] Analyzing '{window_title}'...")
                self._logged_analyze = True

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
            
            if not self._logged_result:
                self._log(f"👁️ [Vision] Result ({elapsed:.2f}s): {log_text}")
                self._logged_result = True
            return result_text

        except Exception as e:
            logger.error(f"Analysis Error: {e}")
            self._log(f"❌ [Vision] Error: {e}", 'error')
            traceback.print_exc()
            return f"Error: {str(e)}"

# Singleton Instance
vision_service = VisionService()

