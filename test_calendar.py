from src.calendar_manager import CalendarManager
import os
import sys

# Ensure we can import from src
sys.path.append(os.getcwd())

def test_auth():
    print("--- Starting Calendar Auth Test ---")
    current_dir = os.getcwd()
    print(f"Current Directory: {current_dir}")
    
    cred_path = 'client_secret.json'
    if not os.path.exists(cred_path):
        print(f"CRITICAL ERROR: {cred_path} not found in {current_dir}")
        return

    print(f"Found {cred_path}. Initializing Manager...")
    cm = CalendarManager(credentials_path=cred_path)
    
    print("Calling authenticate()...")
    try:
        success = cm.authenticate()
        if success:
            print("Authentication SUCCESS!")
            print("Fetching events...")
            events = cm.get_upcoming_events()
            for e in events:
                print(e)
        else:
            print("Authentication FAILED (returned False).")
    except Exception as e:
        print(f"Authentication EXCEPTION: {e}")

if __name__ == "__main__":
    test_auth()
    input("Press Enter to exit...")
