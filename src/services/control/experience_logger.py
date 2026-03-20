
import json
import os
import datetime
import base64
from io import BytesIO

class ExperienceLogger:
    """
    Logs OS Control actions for 'Experience' & 'Learning'.
    Saves to jsonl with screenshot storage logic.
    """
    def __init__(self, log_path="logs/action_history.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
    def log_action(self, instruction, code_executed, success, error_msg=None, before_img=None, after_img=None, reason=None):
        """
        Logs an action sequence.
        Screenshots are saved as separate files to avoid giant JSONL, or base64 thumbnailed?
        For RAG lightness, maybe just save reference path.
        """
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_safe = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save images
        before_path = ""
        after_path = ""
        
        img_dir = "logs/screenshots"
        os.makedirs(img_dir, exist_ok=True)
        
        if before_img:
            before_path = f"{img_dir}/{ts_safe}_before.jpg"
            before_img.save(before_path, quality=50) # Low quality for logs
            
        if after_img:
            after_path = f"{img_dir}/{ts_safe}_after.jpg"
            after_img.save(after_path, quality=50)
            
        # Generate Thumbnails for UI (Base64)
        thumbs = {}
        try:
            if before_img:
                b = before_img.copy()
                b.thumbnail((160, 90))
                buffered = BytesIO()
                b.save(buffered, format="JPEG")
                thumbs["before"] = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
                
            if after_img:
                a = after_img.copy()
                a.thumbnail((160, 90))
                buffered = BytesIO()
                a.save(buffered, format="JPEG")
                thumbs["after"] = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Thumbnail Gen Failed: {e}")

        entry = {
            "timestamp": timestamp,
            "instruction": instruction,
            "code": code_executed,
            "success": success,
            "error": error_msg,
            "reasoning": reason, # Why AI thought it succeeded/failed
            "images": {
                "before": before_path,
                "after": after_path
            },
            "images_b64": thumbs # For Frontend UI only (not typically saved to disk if we want to save space, but here we return it)
        }
        
        # Save to file (omit large b64 if needed, but for now we save structure without b64)
        # We create a clean entry for disk
        disk_entry = entry.copy()
        del disk_entry['images_b64']
        
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(disk_entry, ensure_ascii=False) + "\n")
            
        return entry
