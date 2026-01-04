from ..services.voice_input_manager import voice_input_manager

class VoiceApiMixin:
    """ 音声入力機能を提供するAPI Mixin """
    
    def get_audio_devices(self):
        """マイクデバイス一覧を取得"""
        return voice_input_manager.get_input_devices()

    def start_voice_input(self, device_index=None):
        """録音開始"""
        # JS側から null が来る場合があるので int に変換
        if device_index is not None:
            try:
                device_index = int(device_index)
            except:
                device_index = None
                
        voice_input_manager.start_recording(device_index)
        return {"status": "recording_started"}

    def stop_voice_input(self):
        """
        録音を停止して認識結果を返す
        Note: フロントエンドはこれを await して結果を待つ
        """
        text = voice_input_manager.stop_recording()
        if text:
            return {"status": "success", "text": text}
        else:
            return {"status": "no_speech", "text": ""}

    def configure_voice_hotkey(self, settings):
        """設定からホットキーを適用する"""
        hotkey = settings.get('voice_input_hotkey', 'right ctrl')
        
        # Backendのトグルメソッドを直接登録
        # (toggle_voice_input_hotkey 内で _window の存在チェックを行っているため安全)
        voice_input_manager.set_hotkey(hotkey, self.toggle_voice_input_hotkey)
        return {"status": "success"}

    def toggle_voice_input_hotkey(self):
        """
        ホットキーから呼ばれるトグル処理。
        UIスレッドの外(keyboardスレッド)から呼ばれるため、エラーハンドリングに注意。
        """
        import logging
        logger = logging.getLogger("voice_api")
        
        if not hasattr(self, '_window') or not self._window:
            return

        if voice_input_manager.is_recording:
            # 停止処理
            logger.info("Hotkey: Stop Recording")
            # 1. UIを「処理中」に変更
            self._window.evaluate_js("window.updateMicUiState && window.updateMicUiState('processing')")
            
            # 2. 録音停止＆認識 (ブロッキング処理)
            text = voice_input_manager.stop_recording()
            
            # 3. 結果をUIに送信 (JS側の関数を呼ぶ)
            if text:
                # エスケープ処理
                safe_text = text.replace("'", "\\'").replace("\n", " ")
                self._window.evaluate_js(f"window.insertVoiceText && window.insertVoiceText('{safe_text}')")
            
            # 4. IDLEに戻す
            self._window.evaluate_js("window.updateMicUiState && window.updateMicUiState('idle')")
            
        else:
            # 開始処理
            logger.info("Hotkey: Start Recording")
            voice_input_manager.start_recording() # デフォルトデバイス
            self._window.evaluate_js("window.updateMicUiState && window.updateMicUiState('recording')")
