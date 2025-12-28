from .base import BaseApiMixin

class HistoryApiMixin(BaseApiMixin):
    """
    API methods for History Window (Chat History & Diary).
    """

    # --- History Session Methods ---
    def get_history_sessions(self, keyword=None, favorites_only=False):
        """Fetch list of chat sessions."""
        try:
            return self.services.db_manager.get_sessions(keyword=keyword, favorites_only=favorites_only)
        except Exception as e:
            self.log_to_debug(f"API Error get_history_sessions: {e}", 'error')
            return []

    def get_history_messages(self, session_id):
        """Fetch messages for a specific session."""
        try:
            return self.services.db_manager.get_messages(session_id)
        except Exception as e:
            self.log_to_debug(f"API Error get_history_messages: {e}", 'error')
            return []

    def toggle_history_favorite(self, session_id, is_favorite):
        try:
            return self.services.db_manager.toggle_favorite(session_id, is_favorite)
        except Exception as e:
            self.log_to_debug(f"API Error toggle_history_favorite: {e}", 'error')
            return False

    def delete_history_session(self, session_id):
        try:
            return self.services.db_manager.delete_session(session_id)
        except Exception as e:
            self.log_to_debug(f"API Error delete_history_session: {e}", 'error')
            return False

    def resume_history_session(self, session_id):
        try:
            self.services.user_manager.set_active_session(session_id)
            # Reload Chat UI via window refresh or event
            if self._window:
                self._window.evaluate_js("window.location.reload()")
            return True
        except Exception as e:
            self.log_to_debug(f"API Error resume_history_session: {e}", 'error')
            return False

    def manual_save_session(self):
        try:
            # Usually messages are saved on fly. Maybe force update timestamp?
            # Or perhaps just a placeholder for "Save" feedback.
            return True
        except Exception as e:
            self.log_to_debug(f"API Error manual_save_session: {e}", 'error')
            return False

    def start_new_session(self):
        try:
            self.services.user_manager.start_new_session()
            if self._window:
                self._window.evaluate_js("window.location.reload()")
            return True
        except Exception as e:
            self.log_to_debug(f"API Error start_new_session: {e}", 'error')
            return False

    # --- Phase 89: Diary API ---
    def get_diary_list(self):
        """Fetch list of diaries."""
        try:
            return self.services.db_manager.get_diary_list()
        except Exception as e:
            self.log_to_debug(f"API Error get_diary_list: {e}", 'error')
            return []

    def get_diary_entry(self, diary_id):
        """Fetch specific diary entry."""
        try:
            return self.services.db_manager.get_diary_entry(diary_id)
        except Exception as e:
            self.log_to_debug(f"API Error get_diary_entry: {e}", 'error')
            return None
            
    def generate_diary_manual(self):
        """Debug: Force generate diary for yesterday."""
        try:
            self.services.diary_generator.check_and_generate_diary(force=True)
            return True
        except Exception as e:
            self.log_to_debug(f"API Error generate_diary_manual: {e}", 'error')
            return False
