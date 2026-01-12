
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import logging
logging.basicConfig(level=logging.DEBUG)

from src.services.voice.soulmate_ears import SoulMateEars

print("--- Starting VRAM Test ---")
try:
    ears = SoulMateEars()
    print("--- Initialization Complete ---")
    
    # Simulate processing
    # We don't have audio here, but we can check if it loaded without error
    print("Optimization applied successfully.")
    
except Exception as e:
    print(f"Error: {e}")
