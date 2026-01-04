import requests
import logging
import json
from typing import Optional, Dict, Any

# Configure logger for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DifyClient:
    """
    Dify (Workflow Link) と連携するためのクライントクラスです。
    特定のWorkflow Appを実行し、結果を取得します。
    """
    BASE_URL = "https://api.dify.ai/v1"

    def __init__(self, api_key: str, log_callback=None):
        """
        Args:
            api_key (str): Dify AppのAPI Key (Workflowタイプ)
            log_callback (callable, optional): ログ出力用コールバック関数 (msg: str -> void)
        """
        self.api_key = api_key
        self.log_callback = log_callback
        if not self.api_key:
            self._log("⚠️ Dify API Key is not set.", level="warning")

    def _log(self, message: str, level: str = "info"):
        """内部ログ出力ヘルパー"""
        # Standard logging
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
        
        # UI Callback (System Log)
        if self.log_callback:
            # Prefix with [Dify] for visibility
            self.log_callback(f"[Dify] {message}")

    def fetch_note_article(self, tag: str, user_id: str = "soulmate_user") -> Optional[Dict[str, str]]:
        """
        DifyのWorkflowを実行し、指定されたタグに関連するNote記事情報を取得します。

        Args:
            tag (str): 検索したい記事のタグ (例: "Python", "AI")
            user_id (str): ユーザー識別子 (通常は固定またはセッションID)

        Returns:
            Optional[Dict[str, str]]: 成功時は {"message": "...", "url": "..."} を含む辞書。
                                      失敗時は None。
        """
        if not self.api_key:
            self._log("Dify API Key is missing. Cannot execute workflow.", level="error")
            return None

        url = f"{self.BASE_URL}/workflows/run"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Dify Workflow Input Spec
        payload = {
            "inputs": {
                "tag": tag
            },
            "response_mode": "blocking",
            "user": user_id
        }

        try:
            self._log(f"Connecting to Dify API... (Tag: {tag})")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status() # Raise error for 4xx/5xx

            # Parse Response
            data = response.json()
            
            # Extract outputs based on the specific Workflow Response structure
            # Structure: {"data": {"outputs": {"message": "...", "url": "..."}}}
            outputs = data.get("data", {}).get("outputs", {})
            
            if not outputs:
                self._log(f"Dify response did not contain expected outputs. raw: {data}", level="warning")
                return None

            self._log("Successfully fetched data from Dify.")
            return {
                "message": outputs.get("message", ""),
                "url": outputs.get("url", "")
            }

        except requests.exceptions.RequestException as e:
            self._log(f"Dify API Connection Error: {e}", level="error")
            if e.response is not None:
                self._log(f"Error Response: {e.response.text}", level="error")
            return None
        except Exception as e:
            self._log(f"Unexpected Error during Dify execution: {e}", level="error")
            return None

if __name__ == "__main__":
    # --- USAGE EXAMPLE ---
    # 1. 取得したAPIキーをここに貼り付けてテストしてください
    API_KEY = "app-drlsmEcN9o1qJTxJyJzQtbIz"
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️ エラー: API_KEY が設定されていません。コード内の 'YOUR_API_KEY_HERE' を書き換えてください。")
    else:
        client = DifyClient(api_key=API_KEY)
        
        target_tag = "Python"
        print(f"Testing Dify Workflow with tag: {target_tag}...")
        
        result = client.fetch_note_article(target_tag)
        
        if result:
            print("\n✅ Success!")
            print(f"Message: {result.get('message')}")
            print(f"URL: {result.get('url')}")
        else:
            print("\n❌ Failed to fetch data.")
