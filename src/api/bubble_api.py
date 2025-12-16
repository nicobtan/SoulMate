import logging

logger = logging.getLogger(__name__)

class BubbleApi:
    """
    Mixin for Soul Bubble related API methods.
    """

    def trigger_bubble_action(self, action_id: str):
        """
        Triggered when the user clicks on a Soul Bubble.
        """
        logger.info(f"Bubble API: Action Triggered = {action_id}")
        
        # Here we would delegate to BubbleService or dispatch based on ID
        if hasattr(self, 'bubble_service'):
            return self.bubble_service.handle_action(action_id)
        else:
            logger.error("BubbleService not initialized")
            return {"status": "error", "message": "Service not ready"}
