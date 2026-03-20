import ctypes
from ctypes import wintypes
import time
import logging

logger = logging.getLogger(__name__)

# --- CTYPES STRUCTURES ---
# user32.dll definitions for SendInput
# Reference: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput

INPUT_MOUSE    = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_UNICODE     = 0x0004
KEYEVENTF_SCANCODE    = 0x0008

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION)
    ]

# Load user32.dll
user32 = ctypes.windll.user32

class InputSimulator:
    """
    Directly talks to Windows OS to inject keystrokes via SendInput API.
    Magical teleportation of text directly into the active window! 
    """
    
    @staticmethod
    def send_text(text: str):
        """
        Sends text as Unicode events.
        Ignores keyboard layout (JIS/US) and Current IME state.
        Does NOT use Clipboard.
        """
        if not text: return
        
        logger.debug(f"🔮 [Win32Input] Teleporting text: {text[:10]}...")
        
        for char in text:
            # Create Unicode Key Down Event
            ud_input = INPUT()
            ud_input.type = INPUT_KEYBOARD
            ud_input.union.ki.wVk = 0
            ud_input.union.ki.wScan = ord(char) # Unicode character
            ud_input.union.ki.dwFlags = KEYEVENTF_UNICODE
            
            # Create Unicode Key Up Event
            uu_input = INPUT()
            uu_input.type = INPUT_KEYBOARD
            uu_input.union.ki.wVk = 0
            uu_input.union.ki.wScan = ord(char)
            uu_input.union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            
            # Send both
            user32.SendInput(1, ctypes.byref(ud_input), ctypes.sizeof(ud_input))
            user32.SendInput(1, ctypes.byref(uu_input), ctypes.sizeof(uu_input))
            
            # Tiny sleep might be needed for some legacy apps, but usually instant is fine.
            # time.sleep(0.001) 
            
        return True

    @staticmethod
    def send_vk(vk_code: int, down=True):
        """
        Sends a specific Virtual Key Code (e.g. Enter, Tab).
        """
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.union.ki.wVk = vk_code
        inp.union.ki.wScan = 0
        inp.union.ki.dwFlags = 0 if down else KEYEVENTF_KEYUP
        
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
