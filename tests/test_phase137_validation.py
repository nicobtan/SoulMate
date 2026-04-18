import pytest
import sys
import os
from unittest.mock import MagicMock, patch
import json

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.controller import SoulMateController
from src.services.core.active_engine import ActiveEngine
from src.services.core.character_service import CharacterService

# --- Mock Objects ---

class MockApi:
    def __init__(self):
        self._active_engine = MagicMock()
        self._live2d_window = MagicMock()
        self._live2d_visible = True
        self._config_manager = MagicMock()
        self.log_to_debug = MagicMock()
        
    def _configure_ai(self, settings):
        pass

# --- Tests for Phase 137 ---

def test_controller_stealth_toggle():
    """Live2DManager: is_stealth_mode フラグによるレンダリング停止/再開の正確性"""
    mock_api = MockApi()
    controller = SoulMateController(mock_api)
    
    # 仮想的にGUIの部品をモックする
    controller.stealth_btn = MagicMock()
    controller.status_label = MagicMock()
    
    # 1. Stealth Mode を ON にする
    controller.toggle_stealth()
    
    assert controller.is_stealth is True
    # ActiveEngine にステルスモードが伝播したか
    mock_api._active_engine.set_stealth_mode.assert_called_with(True)
    # JS側に停止命令が送られ、ウィンドウが非表示になったか
    mock_api._live2d_window.evaluate_js.assert_called_with("if(window.setLive2DStealthMode) window.setLive2DStealthMode(true);")
    mock_api._live2d_window.hide.assert_called_once()
    assert mock_api._live2d_visible is False
    
    # 2. Stealth Mode を OFF にする
    controller.toggle_stealth()
    
    assert controller.is_stealth is False
    # ActiveEngine に解除が伝播したか
    mock_api._active_engine.set_stealth_mode.assert_called_with(False)
    # JS側に再開命令が送られ、ウィンドウが表示されたか
    mock_api._live2d_window.evaluate_js.assert_called_with("if(window.setLive2DStealthMode) window.setLive2DStealthMode(false);")
    mock_api._live2d_window.show.assert_called_once()
    assert mock_api._live2d_visible is True


def test_active_engine_stealth_mode_logging():
    """ActiveEngine: Stealthモード中のバックグラウンド思考・感情値更新の継続性"""
    mock_ai_engine = MagicMock()
    mock_callback = MagicMock()
    
    engine = ActiveEngine(
        ai_engine=mock_ai_engine,
        on_message_callback=mock_callback,
        log_callback=MagicMock()
    )
    
    # ステルスモードON
    engine.set_stealth_mode(True)
    assert engine.stealth_mode is True
    mock_ai_engine.set_system_prompt.assert_called() # ステルス用プロンプトへの切り替え確認
    
    # _perform_vision_scan の内部ロジックをテストするため、
    # 依存する vision_service や決定ロジックをモックして、speak アクションを強制発火させる
    with patch('src.services.core.active_engine.vision_service') as mock_vision, \
         patch('src.services.core.proactive_chat_manager.ProactiveChatManager') as MockManager, \
         patch('src.services.vision.window_target_manager.window_target_manager') as mock_target_manager, \
         patch('PIL.ImageGrab.grab') as mock_grab:
        
        # モックの返り値を設定
        mock_grab.return_value.convert.return_value.mode = "RGB"
        mock_vision.analyze_image.return_value = "Test vision text"
        
        mock_manager_instance = MagicMock()
        # 発話(speak)アクションを返すように設定
        mock_manager_instance.decide_next_action.return_value = {
            "action": "speak",
            "text": "バックグラウンドで作業中です。",
            "topic_tag": "work"
        }
        MockManager.return_value = mock_manager_instance
        
        # スキャン実行（スレッドロックがかかるため直接内部メソッドを呼ぶかロックを解除しておく）
        engine._perform_vision_scan()
        
        # 検証：TTS用のペイロード（type="proactive"）ではなく、
        # Stealth用のログペイロード（type="stealth_log"）がコールバックに渡されていること
        mock_callback.assert_called_once()
        called_arg = mock_callback.call_args[0][0]
        data = json.loads(called_arg)
        
        assert data.get("type") == "stealth_log"
        assert data.get("text") == "バックグラウンドで作業中です。"


def test_character_switch_initialization():
    """キャラクター変更: 変更後の設定に基づく初期化"""
    mock_api = MockApi()
    service = CharacterService(mock_api)
    
    # テスト用のプロファイルデータ
    service.profiles = [
        {
            "id": "test_char_01",
            "name": "Test Character",
            "model_id": "test_model",
            "persona_id": "test_persona",
            "voice": {
                "provider": "voicevox",
                "voice_name": "1"
            }
        }
    ]
    
    # api の設定更新メソッドをモック
    mock_api._config_manager.get_all.return_value = {"current_character_id": "test_char_01"}
    mock_api._configure_ai = MagicMock()
    
    # 実行
    result = service.switch_character("test_char_01")
    
    # 検証
    assert result is not None
    assert result["name"] == "Test Character"
    
    # ConfigManager が正しい値で update されたか
    mock_api._config_manager.update.assert_called_once()
    update_args = mock_api._config_manager.update.call_args[0][0]
    assert update_args["current_character_id"] == "test_char_01"
    assert update_args["current_model_id"] == "test_model"
    assert update_args["current_persona_id"] == "test_persona"
    assert update_args["tts_provider"] == "voicevox"
    
    # APIのAI再構成が呼ばれたか
    mock_api._configure_ai.assert_called_once()
    
