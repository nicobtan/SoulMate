import logging
import datetime
import json
import re
from typing import Dict, Any
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
        # Temperature setting for variety
        self.temperature = 0.9
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
                },
                "action_command": {
                    "type": "STRING",
                    "description": "Action tag if needed (e.g. [ACTION:ADD_EVENT|Summary|Time]). Empty if none."
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
                for c in [types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, types.HarmCategory.HARM_CATEGORY_HARASSMENT, types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT]
                for c in [types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, types.HarmCategory.HARM_CATEGORY_HARASSMENT, types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT]
                ],
                temperature=self.temperature
            )
            # Apply Temperature manually if supported or via config? 
            # google-genai SDK 0.x might support it in config or generation_config.
            # types.GenerateContentConfig has 'temperature' field.
            # Temperature applied in init
            # run_config.temperature = self.temperature

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

            # パース処理 (Robust Cleaning)
            if response.text:
                data = self._parse_ai_response(response.text)


            # Log Grounding Info to Mind Tab
            grounding = self._extract_grounding(response)
            if grounding and grounding.get("sources"):
                self._log_thought(f"🌍 [Grounding] Search Results:")
                for source in grounding["sources"]:
                     self._log_thought(f"🔗 [Source] {source['title']} ({source['url'][:40]}...)")
            
            return {
                "text": data.get("response", "") or data.get("text", ""), # Fallback to text if response invalid
                "emotion": data.get("emotion", "neutral"),
                "suggestions": data.get("suggestions", []),
                "action_command": data.get("action_command", ""),
                "grounding_info": grounding
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
            response = self.client.models.generate_content(model=self.reasoning_model, contents=prompt)
            return response.text.strip().replace('"', '')
        except: return None

    def _parse_ai_response(self, raw_text: str) -> Dict[str, Any]:
        """
        AIの応答からJSONを抽出する堅牢なパーサー。
        Markdown記法、余分な空白、説明文などを除去してパースを試みる。
        """
        text = raw_text.strip()
        
        # 1. Markdownコードブロックの除去 (```json ... ```)
        # 大文字小文字無視、改行含む
        match = re.search(r"```(?:json)?\s*(.*)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        
        # 2. それでもパースできない場合、最初と最後の {} を探して抽出する
        if "{" in text:
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if last_brace > first_brace:
                text = text[first_brace : last_brace + 1]

        # 3. JSONパースの試行
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"[AI Engine] JSON Parse Error: {e}")
            logger.error(f"[AI Engine] Failed Text: {raw_text}")
            
            # 4. 最終手段: パース失敗時は、テキスト全体をresponseとして扱う
            return {
                "response": text, # clean text
                "suggestions": [],
                "emotion": "neutral",
                "action_command": ""
            }
