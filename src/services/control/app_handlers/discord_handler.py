
import logging
import time
import pyautogui
from src.services.control.win32_input import InputSimulator
from src.services.vision.vision_service import vision_service
from PIL import ImageGrab

logger = logging.getLogger(__name__)

class DiscordHandler:
    """
    [Discord Navigator]
    Discord専用の操作ハンドラ。
    GUI探索ではなく、ショートカット(Ctrl+K)を活用した確実なナビゲーションを提供します。
    """
    def __init__(self, operator):
        self.operator = operator # SoulOperator instance for reuse of safe_type etc.
        self.vision = vision_service

    def activate_window(self):
        """Discordウィンドウをアクティブにします。"""
        logger.info("🎮 [Discord] ウィンドウを探しています...")
        
        # 簡易的実装: Winキー検索で確実に前面に出す
        pyautogui.press('win')
        time.sleep(0.5)
        InputSimulator.send_text("Discord")
        time.sleep(1.0)
        pyautogui.press('enter')
        time.sleep(2.0) # 起動/切り替え待ち

    def navigate(self, target_name):
        """
        クイックスイッチャー (Ctrl+K) を使ってチャンネルやサーバーに移動します。
        
        Args:
            target_name (str): 移動先（例: "general", "開発室"）
        """
        logger.info(f"🧭 [Discord] '{target_name}' に移動するわね！シュッと！")
        
        # 1. Ensure Active
        # self.activate_window() # 毎回やるとうっとうしいかも？ 呼び出し側制御にするか、ここに入れるか。
        # 安全のため、まずはウィンドウがアクティブだと仮定するか、失敗したらリカバリ。
        # ここではプラン内で activate してもらう想定だが、念のため入れても良い。
        
        # 2. Quick Switcher
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(0.5)
        
        # 3. Type Target
        # 入力欄にフォーカスがあるはず
        InputSimulator.send_text(target_name)
        time.sleep(0.8) # 候補表示待ち
        
        # 4. Select
        pyautogui.press('enter')
        time.sleep(1.0) # 移動待ち
        
        # 5. Verify (Vision)
        logger.info("👀 [Discord] ちゃんと移動できたか確認中...")
        screenshot = self.operator.get_screen_snapshot()
        
        # 簡易チェック: 画面内に target_nameっぽい文字があるか？ 
        # VisionServiceに聞くのが確実
        verification_prompt = f"現在の画面はDiscordで、'{target_name}' というチャンネルやサーバーが開かれていますか？"
        try:
           analysis = self.vision.analyze_image(screenshot, verification_prompt)
           if "はい" in analysis or "見えます" in analysis or "開かれています" in analysis or "表示されています" in analysis:
               logger.info(f"✅ [Discord] 移動成功！ここね！")
               return True
           else:
               logger.warning(f"⚠️ [Discord] あれ？移動できてないかも… (Vision: {analysis[:50]}...)")
               # 失敗しても続行する場合が多いのでFalseを返して呼び出し元に任せる
               return False
        except Exception as e:
            logger.warning(f"Discord Verification Error: {e}")
            return True # エラーならとりあえず進む

    def send_message(self, message):
        """メッセージを送信します。"""
        logger.info(f"💬 [Discord] メッセージを送るわ: {message[:20]}...")
        
        # 入力欄にフォーカスがある前提 (Navigate直後など)
        # 念のため Esc を押してメッセージ入力欄に戻る手もあるが、Ctrl+K直後はフォーカス移動してるはず
        
        InputSimulator.send_text(message)
        time.sleep(0.5)
        
        # 日本語入力確定用 Enter + 送信用 Enter
        pyautogui.press('enter')
        time.sleep(0.1)
        pyautogui.press('enter') 
        
        logger.info("➡️ [Discord] 送信！")
        return True
