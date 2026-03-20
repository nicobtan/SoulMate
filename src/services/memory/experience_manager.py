import logging
import uuid
import chromadb
from chromadb.config import Settings
import datetime

logger = logging.getLogger(__name__)

class ExperienceManager:
    """
    [ExperienceManager]
    SoulMateの「経験記憶」を司るクラス。
    ユーザーからのフィードバック(/ok, /ng)に基づいて、成功パターンと失敗パターンを
    Vector DB (ChromaDB) に保存・検索します。
    """
    def __init__(self):
        # 永続化設定 (メモリではなくファイルに保存)
        self.client = chromadb.PersistentClient(path="memory/chroma_db")
        
        # コレクション（成功用と失敗用）
        self.success_collection = self.client.get_or_create_collection("success_memories")
        self.failure_collection = self.client.get_or_create_collection("failure_memories")

    def recall(self, instruction: str):
        """
        今の状況(instruction)に似た過去の経験を思い出す
        """
        hints = {"success": [], "failure": []}
        
        try:
            # 成功事例の検索
            results_s = self.success_collection.query(query_texts=[instruction], n_results=2)
            if results_s["documents"] and results_s["documents"][0]:
                for doc, meta in zip(results_s["documents"][0], results_s["metadatas"][0]):
                    hints["success"].append(f"以前の成功策: {doc} (ヒント: {meta.get('reason', '')})")

            # 失敗事例の検索
            results_f = self.failure_collection.query(query_texts=[instruction], n_results=2)
            if results_f["documents"] and results_f["documents"][0]:
                for doc, meta in zip(results_f["documents"][0], results_f["metadatas"][0]):
                    hints["failure"].append(f"避けるべき失敗: {doc} (理由: {meta.get('reason', '')})")
                    
        except Exception as e:
            logger.error(f"Recall failed: {e}")
            
        return hints

    def learn(self, instruction, action_plan, result_type, reason=""):
        """
        経験を脳に刻む (/ok, /ng コマンドから呼ばれる)
        """
        try:
            doc_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().isoformat()
            
            metadata = {
                "timestamp": timestamp,
                "reason": reason
            }
            
            if result_type == "SUCCESS":
                self.success_collection.add(
                    documents=[action_plan], # 成功したプランを記憶
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                logger.info(f"🧠 [Memory] 成功体験を記憶しました: {action_plan}")
                
            elif result_type == "FAILURE":
                self.failure_collection.add(
                    documents=[action_plan], # 失敗したプランを「避けるべき」として記憶
                    metadatas=[metadata],
                    ids=[doc_id]
                )
                logger.info(f"🧠 [Memory] 失敗体験を記憶しました: {action_plan} -> {reason}")

        except Exception as e:
            logger.error(f"Learning failed: {e}")

    def create_log_entry(self, instruction, code, success, error_msg, reason, before_img, after_img):
        """
        Action Log用のデータ構造を作成するヘルパーメソッド (Frontend用)
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "timestamp": timestamp,
            "instruction": instruction,
            "code": code,
            "success": success,
            "error": error_msg,
            "reasoning": reason,
            "images_b64": {
                "before": before_img,
                "after": after_img
            } if before_img or after_img else None
        }

# シングルトン
experience_manager = ExperienceManager()
