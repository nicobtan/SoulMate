import win32gui
import win32api
import win32con
import ctypes
from PIL import Image
import threading
import time
import logging
from mss import mss

logger = logging.getLogger(__name__)

class WindowTargetManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(WindowTargetManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.target_hwnd = None
        self.target_title = None
        self.target_rect = None
        self.is_dragging = False
        self.log_callback = None
        self._initialized = True
        
        # Initialize DPI Awareness to ensure coordinates are correct
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            logger.warning(f"Failed to set DPI aware: {e}")

        # Callbacks
        self.log_callback = None
        self.target_callback = None # New: For UI Updates

    def set_log_callback(self, callback):
        self.log_callback = callback
        
    def set_target_callback(self, callback):
        """Sets callback for target change events (appName, isLocked)"""
        self.target_callback = callback

    def _log(self, message, type='info'):
        logger.info(message)
        if self.log_callback:
            self.log_callback(message, type=type)

    def _notify_ui(self):
        """Notifies UI of current target state"""
        if self.target_callback:
            app_name = self.target_title if self.target_hwnd else "Scanning..."
            is_locked = bool(self.target_hwnd)
            self.target_callback(app_name, is_locked)

    def start_drag_session(self):
        """Starts a background thread to monitor drag end."""
        if self.is_dragging:
            return
        
        self.is_dragging = True
        self._log("👁️ [Vision] Target Drag Started...", type='vision')
        threading.Thread(target=self._drag_loop, daemon=True).start()

    def _drag_loop(self):
        """Monitors mouse state until left click is released."""
        while self.is_dragging:
            if win32api.GetAsyncKeyState(win32con.VK_LBUTTON) >= 0:
                self._on_drop()
                break
            time.sleep(0.05)

    def _on_drop(self):
        """Handles the drop event: identifies the window under cursor."""
        self.is_dragging = False
        
        try:
            x, y = win32api.GetCursorPos()
            hwnd = win32gui.WindowFromPoint((x, y))
            
            # Walk up to find the root window if we hit a child
            while win32gui.GetParent(hwnd):
                hwnd = win32gui.GetParent(hwnd)

            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd) # (left, top, right, bottom)
            
            if not title:
                self._log("👁️ [Vision] Target dropped on empty space. Target cleared.", type='vision')
                self.clear_target()
                return

            self.lock_target(hwnd, title, rect)

        except Exception as e:
            logger.error(f"Error in _on_drop: {e}")
            self._log(f"⚠️ [Vision] Target acquisition failed: {e}", type='error')

    def lock_target(self, hwnd, title, rect):
        self.target_hwnd = hwnd
        self.target_title = title
        self.target_rect = rect
        self._log(f"👁️ [Vision] 🎯 Target Locked: {title}", type='vision')
        self._notify_ui()

    def clear_target(self):
        self.target_hwnd = None
        self.target_title = None
        self.target_rect = None
        self._log("👁️ [Vision] Target Disengaged.", type='vision')
        self._notify_ui()

    def get_target_image(self) -> Image.Image:
        """
        Captures the target window area using mss (Fast & Game compatible).
        """
        try:
            # If no target, capture primary monitor
            if not self.target_hwnd:
                with mss() as sct:
                     # monitor 1 is usually primary
                     # mss grab returns a numpy array compatible object, or we can use PIL conv
                     sct_img = sct.grab(sct.monitors[1])
                     return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Check if minimized
            if win32gui.IsIconic(self.target_hwnd):
                self._log("⚠️ [Vision] Target is minimized. Skipping capture.", type='vision')
                return None

            # Get coordinates
            try:
                rect = win32gui.GetWindowRect(self.target_hwnd)
                self.target_rect = rect
            except Exception:
                self._log("⚠️ [Vision] Target window lost.", type='vision')
                self.clear_target()
                return None

            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                self._log("⚠️ [Vision] Target size invalid.", type='vision')
                return None

            # Prepare mss dict
            monitor = {"top": top, "left": left, "width": width, "height": height}

            with mss() as sct:
                sct_img = sct.grab(monitor)
                # mss returns BGRA, convert to RGB
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                return img

        except Exception as e:
            logger.error(f"Capture failed (mss): {e}")
            self._log(f"⚠️ [Vision] Capture failed: {e}", type='error')
            return None

# Singleton
window_target_manager = WindowTargetManager()
