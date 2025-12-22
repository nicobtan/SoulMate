
import os
import json
import time
import sys
import logging
import urllib.parse

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate_fillers")

# Add project root to path
sys.path.append(os.getcwd())

try:
    from src.services.voice_service import VoiceService
except ImportError:
    print("Error: Could not import VoiceService. Make sure you are running from project root.")
    sys.exit(1)

# Configuration
CONFIG_PATH = "settings/config.json"
OUTPUT_DIR = "dist/audio/fillers"
TARGET_VOICE_TYPE = "Aoede" # Default, will try to read from config

# Filler Phrases
FILLERS = [
    # Thinking / Pause
    {"text": "んー、そうねぇ…", "name": "thinking_01"},
    {"text": "えっと…", "name": "thinking_02"},
    {"text": "ふふっ、それはね…", "name": "thinking_03"},
    {"text": "あ、それって…", "name": "thinking_04"},
    {"text": "ん〜、考えさせてね…", "name": "thinking_05"},
    {"text": "ちょっと待ってね", "name": "wait_01"},
    {"text": "OK、わかったわ", "name": "ack_01"},
]

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def main():
    # 1. Prepare Directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logger.info(f"Created directory: {OUTPUT_DIR}")

    # 2. Config & Init
    config = load_config()
    api_key = config.get("api_key")
    voice_type = config.get("voice_type", TARGET_VOICE_TYPE)
    
    if not api_key:
        logger.error("API Key not found in config.json")
        return

    service = VoiceService()
    service.set_api_key(api_key)
    
    # Override output dir to fillers specific
    service.output_dir = OUTPUT_DIR

    logger.info(f"Starting Filler Generation using Voice: {voice_type}")
    
    # 3. Batch Generation
    for item in FILLERS:
        text = item["text"]
        name = item["name"]
        
        logger.info(f"Generating: {text} -> {name}.mp3")
        
        try:
             # Use Gemini provider explicitly
            path = service.generate_voice(text, voice_name=voice_type, provider="gemini")
            
            if path:
                # path is web path 'audio/filename.mp3' (from voice_service changes)
                # File is locally at service.output_dir/filename.mp3
                
                # Unquote to handle Japanese filenames correctly
                generated_filename = urllib.parse.unquote(os.path.basename(path))
                source_path = os.path.join(service.output_dir, generated_filename)
                
                target_filename = f"{name}.wav"
                target_path = os.path.join(service.output_dir, target_filename)
                
                # Verify source exists
                if os.path.exists(source_path):
                    # Remove target if exists
                    if os.path.exists(target_path):
                        try:
                            # Try simple remove
                            os.remove(target_path)
                        except OSError as e:
                            logger.warning(f"Could not remove existing target: {e}")
                    
                    try:
                        os.rename(source_path, target_path)
                        logger.info(f"✅ Saved: {target_path}")
                    except OSError as e:
                        logger.error(f"❌ Rename failed: {e}")
                else:
                    logger.error(f"❌ Source file not found: {source_path}")
            else:
                logger.error(f"❌ Failed to generate: {text}")

            # Sleep to avoid rate limits
            time.sleep(2.0)
            
        except Exception as e:
            logger.error(f"Error processing {text}: {e}")

    logger.info("All Done!")

if __name__ == "__main__":
    main()
