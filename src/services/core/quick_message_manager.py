
import json
import os
import logging

logger = logging.getLogger(__name__)

class QuickMessageManager:
    """
    よく使う定型文メッセージを管理するクラス
    settings/quick_messages.json を読み書きします。
    """
    def __init__(self, file_path="settings/quick_messages.json"):
        self.file_path = os.path.join(os.getcwd(), file_path)
        self.messages = []
        self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            # デフォルトの定型文を作成
            self.messages = [
                "/do YouTubeで音楽を再生して",
                "/do 今日のニュースを教えて",
                "/do アークナイツの攻略動画を探して",
                "/do 作業用BGMを流して",
                "/do スクリーンショットを撮って"
            ]
            self.save()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load quick messages: {e}")
            self.messages = []

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quick messages: {e}")

    def get_messages(self):
        # 毎回ロードし直すと、ファイルを直接編集した時に反映されやすい
        self._load() 
        return self.messages

# シングルトンインスタンス
quick_message_manager = QuickMessageManager()
