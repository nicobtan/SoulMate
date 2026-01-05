import json
import os
import logging
logger = logging.getLogger("character_service")

class CharacterService:
    def __init__(self, api_instance):
        self.api = api_instance
        self.profiles = []
        self.profiles_path = os.path.join(os.getcwd(), "profiles", "characters.json")
        self.load_profiles()

    def load_profiles(self):
        """characters.json からプロファイルをロード"""
        if not os.path.exists(self.profiles_path):
            logger.warning(f"Profiles not found at {self.profiles_path}")
            return
        
        try:
            with open(self.profiles_path, "r", encoding="utf-8") as f:
                self.profiles = json.load(f)
            logger.info(f"Loaded {len(self.profiles)} character profiles.")
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")

    def get_profiles(self):
        return self.profiles

    def get_profile_by_id(self, profile_id):
        return next((p for p in self.profiles if p["id"] == profile_id), None)

    def switch_character(self, profile_id):
        """
        キャラクターを切り替え、関連する設定を一括更新する
        """
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            logger.error(f"Profile {profile_id} not found.")
            return False
        
        logger.info(f"Switching character to: {profile['name']} ({profile_id})")
        
        # 1. Configの更新 (永続化)
        self.api._config_manager.set("current_character_id", profile["id"])
        self.api._config_manager.set("current_model_id", profile["model_id"])
        self.api._config_manager.set("current_persona_id", profile["persona_id"])
        
        # Voice設定も更新 (TTSプロバイダー等が異なる場合に対応)
        if "voice" in profile:
            voice_conf = profile["voice"]
            # プロバイダー設定があれば更新 (例: gemini -> voicevox)
            if "provider" in voice_conf:
                self.api._config_manager.set("tts_provider", voice_conf["provider"])
            if "voice_name" in voice_conf:
                self.api._config_manager.set("voice_name", voice_conf["voice_name"])
        
        # 2. AI Engine / Persona の再構成
        # 最新のConfigを取得して反映
        new_settings = self.api._config_manager.get_all()
        # Active Engineの再設定も必要かもしれないが、とりあえずAI Engine周りを更新
        if hasattr(self.api, '_configure_ai'):
            self.api._configure_ai(new_settings)
            
        return profile
