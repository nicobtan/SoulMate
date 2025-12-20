import sys
import os

print("Python Executable:", sys.executable)
try:
    import requests
    print("Requests module found:", requests.__version__)
except ImportError as e:
    print("Requests module import failed:", e)

try:
    from src.services.voice_service import VoiceService
    print("VoiceService class imported.")
    
    vs = VoiceService()
    print("VoiceService initialized successfully.")
    print("Output Dir:", vs.output_dir)
    print("Exists:", os.path.exists(vs.output_dir))
    
except Exception as e:
    print(f"VoiceService Init Test Failed: {e}")
    import traceback
    traceback.print_exc()
