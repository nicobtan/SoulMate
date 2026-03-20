import yaml
import os
import logging
from datetime import datetime

logger = logging.getLogger("memory_service")

class MemoryService:
    def __init__(self, memory_file="settings/learned_facts.yaml"):
        # Ensure directory exists
        self.memory_file = os.path.join(os.getcwd(), memory_file)
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        
        # Init file if not exists
        if not os.path.exists(self.memory_file):
            self._save_data({"facts": []})

    def save_learned_fact(self, category: str, content: str) -> str:
        """
        ユーザーとの会話から得た新しい事実、訂正事項、ユーザーの好みを記憶ファイルに保存します。
        
        Args:
            category: 情報の分類 (例: 'preference', 'correction', 'definition', 'user_profile')
            content: 記録する具体的な内容 (例: '「ネタ」という言葉は、文脈がない限り「寿司ネタ」を指す')
        """
        
        # 新しいデータを作成
        new_entry = {
            "category": category,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        data = self._load_data()
        
        # 重複チェック (簡易) - 同じ内容が直近にあれば保存しない等も可能だが、今回は単純追記
        data["facts"].append(new_entry)
        
        if self._save_data(data):
            logger.info(f"📝 [Memory] Saved Fact: [{category}] {content}")
            return f"情報を記録しました: [{category}] {content}"
        else:
            return "エラー: 情報の記録に失敗しました。"

    def get_learned_facts_text(self) -> str:
        """
        システムプロンプトに埋め込むためのテキスト形式で事実を返す。
        """
        data = self._load_data()
        facts = data.get("facts", [])
        
        if not facts:
            return "(No learned facts yet)"
            
        # フォーマット: "- [Category] Content (Date)"
        lines = []
        for fact in facts:
            cat = fact.get('category', 'unknown')
            con = fact.get('content', '')
            ts = fact.get('timestamp', '')
            lines.append(f"- [{cat}] {con} ({ts})")
            
        return "\n".join(lines)

    def _load_data(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    # Migration: learned_facts -> facts
                    if "learned_facts" in data and "facts" not in data:
                        data["facts"] = data.pop("learned_facts")
                    
                    if "facts" not in data:
                        data["facts"] = []
                    return data
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
        return {"facts": []}

    def _save_data(self, data):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False
