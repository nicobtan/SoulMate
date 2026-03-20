import webbrowser
import logging
import subprocess
import os
import shutil
from src.services.system.monitor_manager import monitor_manager

logger = logging.getLogger(__name__)

class BrowserHelper:
    def open_url(self, url, new_window=True):
        """
        Opens a URL in Chrome on the specific target monitor if possible.
        Falls back to default browser.
        """
        try:
            # 1. Get Target Monitor Info
            target_monitor = monitor_manager.get_target_monitor()
            
            # 2. Try to find Chrome
            chrome_path = None
            system_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            for p in system_paths:
                if os.path.exists(p):
                    chrome_path = p
                    break
            
            # 3. Launch Chrome with Args if found
            if chrome_path and target_monitor:
                x = target_monitor.x
                # Y Offset to lower the window slightly (Requested by User)
                y = target_monitor.y + 50
                # Force window position using a separate user data directory
                # This ensures it doesn't merge into an existing Chrome instance on the main monitor.
                profile_dir = os.path.join(os.getcwd(), "chrome_data_soulmate")
                cmd = [
                    chrome_path,
                    url,
                    "--new-window",
                    f"--window-position={x},{y}",
                    f"--window-size={1280},{960}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-gpu", # Prevent black screen capture
                    "--force-device-scale-factor=1" # Ensure consistent coordinate mapping
                ]
                
                logger.info(f"🌐 [BrowserHelper] Launching Chrome (Isolated) on Monitor {target_monitor.name} at ({x}, {y})")
                subprocess.Popen(cmd)
                return True
                
            # 4. Fallback
            logger.info(f"🌐 [BrowserHelper] Chrome not found or Monitor issue. Fallback to default.")
            if new_window:
                webbrowser.open_new(url)
            else:
                webbrowser.open(url)
            return True
            
        except Exception as e:
            logger.error(f"❌ [BrowserHelper] Failed to open URL: {e}")
            return False
