class CharacterApiMixin:
    """
    キャラクター切り替え機能を提供するAPI
    """
    def get_character_profiles(self):
        """利用可能なキャラクター一覧を返す"""
        # serviceがまだ初期化されていない場合のガード
        if not hasattr(self, 'character_service'):
            return []
        return self.character_service.get_profiles()

    def switch_character(self, profile_id):
        """
        指定されたIDのキャラクターに切り替える。
        成功した場合、フロントエンド側で必要なモデルIDなどを返す。
        """
        if not hasattr(self, 'character_service'):
            return {"status": "error", "message": "Service not initialized"}
        
        result = self.character_service.switch_character(profile_id)
        
        if result:
            return {
                "status": "success",
                "profile": result
            }
        else:
            return {"status": "error", "message": "Profile not found"}
