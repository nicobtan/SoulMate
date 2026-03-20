
from src.services.core.quick_message_manager import quick_message_manager

class QuickMessageApiMixin:
    def get_quick_messages(self):
        """
        Returns the list of quick messages from the manager.
        Called via window.pywebview.api.get_quick_messages()
        """
        return {"messages": quick_message_manager.get_messages()}
