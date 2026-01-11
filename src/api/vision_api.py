import logging
from src.services.vision.window_target_manager import window_target_manager

logger = logging.getLogger(__name__)

class VisionApiMixin:
    """
    Mixin for Vision-related API methods.
    """

    def start_target_drag(self):
        """
        Starts the Window Target Drag session.
        Called when the user clicks/holds the target icon in the frontend.
        """
        try:
            logger.info("Starting Target Drag...")
            window_target_manager.start_drag_session()
            return {"status": "started"}
        except Exception as e:
            logger.error(f"Failed to start drag: {e}")
            return {"error": str(e)}

    def clear_vision_target(self):
        """
        Clears the current vision target.
        """
        window_target_manager.clear_target()
        return {"status": "cleared"}

    def get_target_info(self):
        """
        Returns current target info for debugging/UI.
        """
        return {
            "hwnd": window_target_manager.target_hwnd,
            "title": window_target_manager.target_title,
            "rect": window_target_manager.target_rect
        }
