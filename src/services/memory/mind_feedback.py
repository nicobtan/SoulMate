import logging
import json
import time
from datetime import datetime
from src.services.memory.db_manager import DatabaseManager
from src.services.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class MindFeedbackService:
    def __init__(self, api_container):
        self.api = api_container
        self.db_manager = DatabaseManager()
        self.memory_manager = MemoryManager()

    def analyze_and_save(self, history_messages: list):
        """
        Analyzes the conversation history to extract deep insights/philosophy.
        Saves the result to SQLite (insights table) and ChromaDB.
        """
        if not history_messages or len(history_messages) < 2:
            logger.warning("[MindFeedback] Not enough history to analyze.")
            return

        # 1. Prepare Context (Last 20 messages)
        relevant_history = history_messages[-20:]
        context_text = ""
        for msg in relevant_history:
            role = msg.get('role', 'unknown')
            content = msg.get('text') or msg.get('content', '')
            context_text += f"{role}: {content}\n"

        # 2. AI Analysis (Gemini)
        prompt = f"""
[System Instruction]
あなたはユーザーの「精神的パートナー (SoulMate)」です。
以下の直近の会話ログから、ユーザーの「深層心理」「哲学的価値観」「重要な洞察」を抽出してください。
表面的な会話（挨拶、天気、単なる事実）は無視し、**長期的に記憶すべき概念**のみを選んでください。

[Input Chat Log]
{context_text}

[Output Requirement]
JSON形式で出力してください。
{{
    "title": "短いタイトル (例: 愛の定義について)",
    "points": [
        "要点1 (具体的な文脈)",
        "要点2 (抽象化された結論)"
    ],
    "summary": "AIが学んだことの要約"
}}
"""
        try:
            logger.info("[MindFeedback] Analyzing conversation for insights...")
            # Use raw response to avoid Chat JSON wrapping conflict
            response_text = self.api._ai_engine.generate_raw_response(prompt)
            
            if not response_text:
                logger.warning("[MindFeedback] AI returned no text.")
                return

            # Parse JSON
            insight_data = self._parse_json_response(response_text)
            if not insight_data:
                logger.warning("[MindFeedback] Failed to parse AI response.")
                return

            title = insight_data.get('title', 'Untitled Insight')
            points = insight_data.get('points', [])
            summary = insight_data.get('summary', '')

            # Combine points into content text
            content_text = f"{summary}\n\n" + "\n".join([f"- {p}" for p in points])
            
            # 3. Save to SQLite (insights table)
            insight_id = self.db_manager.add_insight(title, content_text)
            logger.info(f"[MindFeedback] Saved to DB. ID: {insight_id}, Title: {title}")

            # 4. Save to ChromaDB (Long-term Memory)
            if self.memory_manager.collection:
                doc_id = f"insight_{int(time.time())}"
                embed_text = f"[Deep Insight] {title}\n{content_text}"
                
                self.memory_manager.collection.add(
                    documents=[embed_text],
                    metadatas=[{
                        "timestamp": datetime.now().isoformat(),
                        "type": "insight",
                        "related_db_id": insight_id
                    }],
                    ids=[doc_id]
                )
                logger.info("[MindFeedback] Embeddings saved to ChromaDB.")

            return insight_data

        except Exception as e:
            logger.error(f"[MindFeedback] Analysis failed: {e}", exc_info=True)
            return None

    def _parse_json_response(self, response):
        """Parses AI response which might be a dict or a string."""
        try:
            if isinstance(response, dict):
                # Ensure it has keys we need, or maybe it's nested
                if 'text' in response: return self._extract_json_from_str(response['text'])
                return response
            
            if isinstance(response, str):
                return self._extract_json_from_str(response)
                
        except Exception as e:
            logger.error(f"JSON Parse Error: {e}")
        return None

    def _extract_json_from_str(self, text):
        import re
        try:
            # Find JSON block ```json ... ``` or just { ... }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(text)
        except:
            return None
