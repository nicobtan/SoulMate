import logging
import traceback

logger = logging.getLogger(__name__)

class UserApiMixin:
    def get_user_profile(self):
        """Returns the raw YAML string of the user profile."""
        if not hasattr(self, 'user_manager') or not self.user_manager:
            return {"status": "error", "message": "User Manager not initialized"}
        
        try:
            raw_yaml = self.user_manager.get_raw_profile()
            return {"status": "success", "data": raw_yaml}
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {"status": "error", "message": str(e)}

    def save_user_profile(self, yaml_content):
        """Saves the raw YAML string to the user profile."""
        if not hasattr(self, 'user_manager') or not self.user_manager:
            return {"status": "error", "message": "User Manager not initialized"}
        
        try:
            success = self.user_manager.save_raw_profile(yaml_content)
            if success:
                # Re-configure AI to reflect changes immediately
                # self._configure_ai is available in both HeadlessApi and Api
                settings = self._config_manager.get_all()
                self._configure_ai(settings)
                logger.info("User profile updated and AI re-configured.")
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Failed to save profile"}
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}\n{traceback.format_exc()}")
            return {"status": "error", "message": str(e)}
