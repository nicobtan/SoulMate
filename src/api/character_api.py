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

    def reload_character_profiles(self):
        """プロファイルを再読み込みして返す"""
        if hasattr(self, 'character_service'):
            self.character_service.reload_profiles()
            return {"status": "success", "profiles": self.character_service.get_profiles()}
        return {"status": "error", "message": "Service not initialized"}

    def switch_character(self, profile_id):
        """
        指定されたIDのキャラクターに切り替える。
        成功した場合、フロントエンド側で必要なモデルIDなどを返す。
        """
        if not hasattr(self, 'character_service'):
            return {"status": "error", "message": "Service not initialized"}
        
        result = self.character_service.switch_character(profile_id)
        
        if result:
            # 3. Main Windowへの通知 (Live2Dモデルの即時切り替え)
            if hasattr(self, '_window') and self._window:
                import json
                # Live2DManagerがグローバルにある前提
                # configを作る
                config = {
                    "scale": result.get("scale", 1.0),
                    "x": result.get("x", 0),
                    "y": result.get("y", 0)
                }
                js_code = f"if(window.live2dManager) window.live2dManager.switchModel('{result['model_id']}', {json.dumps(config)});"
                self._window.evaluate_js(js_code)
                print(f"[CharacterApi] Notified Main Window to switch model: {result['model_id']}")

            return {
                "status": "success",
                "profile": result
            }
        else:
            return {"status": "error", "message": "Profile not found"}
