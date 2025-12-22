import logging
import datetime
import json
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.api_key = None
        self.client = None
        # モデル定義 (Defaults)
        self.reasoning_model = "gemini-3-flash-preview" 
        self.tts_model = "gemini-2.5-flash-preview-tts"
        self.system_instruction = "You are a helpful AI assistant."
        self.use_search = True
        
        # Let's check the user request block code again.
        # self.reasoning_model = "gemini-3-flash-preview"
        # self.tts_model = "gemini-2.5-flash-preview-tts"
        
        # OK, I will paste the user's code structure but I will be careful.
        # Actually I think "gemini-3-flash-preview" is hypothetical or very new.
        # But I must follow user instruction.
        
        self.system_instruction = "You are a helpful AI assistant."
        self.use_search = True
        self.mind_logger = None # Callback for Mind Logs

    def set_mind_logger(self, callback):
        self.mind_logger = callback

    def _log_thought(self, thought):
        if self.mind_logger:
            self.mind_logger(thought)

    def configure(self, api_key, reasoning_model=None, tts_model=None, system_instruction=None):
        self.api_key = api_key
        if reasoning_model: self.reasoning_model = reasoning_model
        if tts_model: self.tts_model = tts_model
        if system_instruction: self.system_instruction = system_instruction
            
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"AIEngine Configured.\n - Reasoning: {self.reasoning_model}")
            except Exception as e:
                logger.error(f"Client Init Error: {e}")

    def set_system_prompt(self, prompt_text):
        self.system_instruction = prompt_text

    def generate_response(self, message, context=None, image=None):
        """Native JSONモードを使用して応答を生成"""
        if not self.client:
            return {"text": "API Key error.", "emotion": "sad", "suggestions": []}

        # ★重要: 出力スキーマの定義 (AIはこの形以外を返せなくなる)
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "response": {"type": "STRING", "description": "Response text. Keep it natural."},
                "emotion": {"type": "STRING", "description": "Emotion tag (happy, sad, neutral, etc)."},
                "suggestions": {
                    "type": "ARRAY", 
                    "items": {"type": "STRING"},
                    "description": "4 specific follow-up suggestions from user perspective."
                }
            },
            "required": ["response", "emotion", "suggestions"]
        }

        try:
            # コンテキスト構築
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            full_prompt = f"Current Time: {now}\n{context}\nUser: {message}"

            # Log Thinking Process
            self._log_thought(f"🤔 Input Analysis:\n- Time: {now}\n- Context: {len(str(context))} chars")
            self._log_thought(f"🧠 Reasoning...\nTargeting Model: {self.reasoning_model}")

            # Config設定
            tools = [types.Tool(google_search=types.GoogleSearch())] if self.use_search and not image else []
            
            run_config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                tools=tools,
                response_mime_type="application/json", # ★JSONモード強制
                response_schema=response_schema,       # ★スキーマ適用
                safety_settings=[
                    types.SafetySetting(category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE)
                    for c in [types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, types.HarmCategory.HARM_CATEGORY_HARASSMENT, types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT]
                ]
            )

            # 生成実行
            contents = [full_prompt]
            if image: contents.append(image)

            # User specified "gemini-3-flash-preview". I will try to use it, but if it fails I might need to fallback.
            # However, I will stick to the user's requested code exactly.
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=run_config
            )

            # パース処理 (json.loadsのみでOK)
            if response.text:
                data = json.loads(response.text)
                return {
                    "text": data.get("response", ""), 
                    "emotion": data.get("emotion", "neutral"),
                    "suggestions": data.get("suggestions", []),
                    "grounding_info": self._extract_grounding(response)
                }
            
            return {"text": "Error: Empty response", "emotion": "sad", "suggestions": []}

        except Exception as e:
            logger.error(f"Gen Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"text": "エラーが発生しました。", "emotion": "sad", "suggestions": []}

    def generate_tts_with_gemini(self, text):
        """TTS生成 (テキストのみ渡す)"""
        try:
            config = types.GenerateContentConfig(response_modalities=["AUDIO"])
            return self.client.models.generate_content(
                model=self.tts_model,
                contents=text, # ここには純粋なテキストのみが入る
                config=config
            )
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None

    def _extract_grounding(self, response):
        # (既存のGrounding抽出ロジックそのまま)
        try:
            candidates = getattr(response, 'candidates', [])
            if candidates and hasattr(candidates[0], 'grounding_metadata'):
                gm = candidates[0].grounding_metadata
                sources = []
                for chunk in getattr(gm, 'grounding_chunks', []):
                    if hasattr(chunk, 'web') and chunk.web:
                        sources.append({"title": chunk.web.title, "url": chunk.web.uri})
                return {"sources": sources} if sources else None
        except:
            return None

    def generate_proactive_message(self, context=None):
        prompt = "User is idle. Initiate a conversation naturally. Suggest a topic for the user."
        if context: prompt += f"\nContext: {context}"
        return self.generate_response(prompt)

    def generate_title_summary(self, conversation_text):
        if not self.client: return None
        prompt = f"Generate a short title (max 20 chars) in Japanese for this conversation:\n{conversation_text[:500]}"
        try:
            # Title generation doesn't strict JSON mode usually but consistentcy helps.
            # Using text mode for title is simpler.
            response = self.client.models.generate_content(model=self.reasoning_model, contents=prompt)
            return response.text.strip().replace('"', '')
        except: return None
