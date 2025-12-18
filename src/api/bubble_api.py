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

    def generate_bubble(self):
        """
        Generates a smart bubble based on context (Time/Interest).
        Triggered by UI Button.
        """
        logger.info(f"API: Smart Bubble Generation Request")
        if hasattr(self, 'bubble_service'):
            # Use get_smart_bubble for dynamic content
            bubble = self.bubble_service.get_smart_bubble()
            if bubble:
                # Must ensure it's registered in active bubbles (get_smart_bubble does NOT add to active dict usually? Wait check service)
                # create_smart_bubble DOES register it in _active_bubbles in the service code I saw earlier? 
                # Let's check service code: 
                # "packet = ...; self._active_bubbles[action_id] = packet; return packet" 
                # Yes, get_smart_bubble adds it to _active_bubbles.
                return bubble
            else:
                return {"status": "skipped", "message": "No bubble generated (Limit or Duplicate)"}
        return {"status": "error", "message": "Service not ready"}
