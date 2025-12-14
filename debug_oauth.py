import sys
import os

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.calendar_manager import CalendarManager

def test_auth():
    print("--- FORCE AUTH TEST ---")
    print("Initializing CalendarManager...")
    cm = CalendarManager()
    
    print("Calling authenticate()...")
    
    def status_callback(msg, type):
        print(f"[CALLBACK] {type}: {msg}")
        
    result = cm.authenticate(status_callback=status_callback)
    
    if result:
        print("SUCCESS: Authentication completed.")
        try:
            events = cm.get_upcoming_events()
            print("Events:", events)
        except Exception as e:
            print(f"Auth success but event fetch failed: {e}")
    else:
        print("FAILURE: Authentication returned False.")

if __name__ == "__main__":
    test_auth()
