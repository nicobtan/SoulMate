import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.voice.soulmate_ears import SoulMateEars

def main():
    print("🤖 Initializing SoulMate Ears (Large-v3 + SpeechBrain)...")
    print("   Please wait, loading heavy models...")
    
    try:
        ears = SoulMateEars(stt_model_size="large-v3", device="cuda")
        print("✅ Initialization Complete. Listening for voice...")
        print("   (Speak into your microphone. Ctrl+C to exit)")
        
        while True:
            # Listening loop
            result = ears.listen_and_process(timeout=None) # Infinite wait until sound
            
            if result:
                text = result['text']
                emotion = result['emotion']
                conf = result['confidence']
                
                print("\n" + "="*40)
                print(f"🎤 Text   : {text}")
                print(f"❤️ Emotion: {emotion} (Confidence: {conf:.2f})")
                print("="*40 + "\n")
                
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
