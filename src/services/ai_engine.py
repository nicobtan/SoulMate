import logging
import datetime
import json
import re
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.api_key = None
        self.model_name = "gemini-2.5-flash-lite"
        self.client = None
        self.chat_session = None
        self.history = []
        self.system_instruction = "You are a helpful AI assistant."
        self.use_search = True # Enable Grounding by default for SoulMate

    def configure(self, api_key, model_name=None, system_instruction=None):
        """Configures the AI Engine with new settings."""
        self.api_key = api_key
        if model_name:
            self.model_name = model_name
        if system_instruction:
            self.system_instruction = system_instruction
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.chat_session = None 
                logger.info(f"AIEngine configured. Model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to configure Gemini Client: {e}")

    def set_system_prompt(self, prompt_text):
        """Updates the system prompt and resets the session."""
        logger.info("Updating System Prompt from Persona.")
        self.system_instruction = prompt_text
        self.chat_session = None

    def _get_chat_session(self, tools=None):
        """Initializes or returns the chat session."""
        if self.chat_session is None:
            if not self.client:
                raise ValueError("Client not initialized. Call configure() first.")
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                response_mime_type="text/plain", 
                tools=tools
            )
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=config,
                history=self.history 
            )
        return self.chat_session

    def _parse_toon_response(self, raw_text: str) -> dict:
        """
        AIの応答からTOON (Token-Oriented Object Notation) を抽出する。
        YAMLライクな構造を正規表現で解析する。
        """
        text = raw_text.strip()
        
        # Clean Markdown wrapper
        text = re.sub(r'^```(yaml|toon|json)?', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'```$', '', text, flags=re.MULTILINE)
        text = text.strip()

        res_text = ""
        emotion = "neutral"
        suggestions = []

        # Parse 'text:'
        # TOONの階層構造（response -> text）またはフラットな構造に対応
        text_match = re.search(r'[\s]*text:\s*(.*?)(?=\n[\s]*(?:emotion|suggestions|response):|$)', text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if not text_match:
             # フラットな 'response:' も一応チェック
             text_match = re.search(r'^response:\s*(.*?)(?=\n(?:emotion|suggestions):|$)', text, re.DOTALL | re.MULTILINE | re.IGNORECASE)

        if text_match:
            res_text = text_match.group(1).strip()
            # 引用符で囲まれている場合は除去 (TOONの緩い仕様への配慮)
            if len(res_text) >= 2:
                if (res_text.startswith('"') and res_text.endswith('"')) or (res_text.startswith("'") and res_text.endswith("'")):
                    res_text = res_text[1:-1].strip()
        else:
            # Fallback
            res_text = text

        # Parse 'emotion:'
        emo_match = re.search(r'^emotion:\s*(.*?)$', text, re.MULTILINE | re.IGNORECASE)
        if emo_match:
            emotion = emo_match.group(1).strip().lower()

        # Parse 'suggestions:'
        sug_match = re.search(r'^suggestions:\s*(.*?)$', text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
        if sug_match:
            sug_block = sug_match.group(1)
            suggestions = re.findall(r'^[\s]*-[\s]*(.+)$', sug_block, re.MULTILINE)
            suggestions = [s.strip() for s in suggestions if s.strip()]

        return {
            "response": res_text,
            "text": res_text,
            "emotion": emotion,
            "suggestions": suggestions
        }

    def _parse_ai_response(self, raw_text: str) -> dict:
        """
        AIの応答をパースする。TOON形式を優先し、失敗した場合はJSONを試みる。
        """
        # 1. TOONパースを試行
        if re.search(r'^(?:response|text|emotion|suggestions):', raw_text, re.MULTILINE | re.IGNORECASE):
            return self._parse_toon_response(raw_text)
            
        # 2. JSONパース (後方互換性)
        text = raw_text.strip()
        if "{" in text:
            # Join lines to handle multi-line JSON if needed, but risky for text
            try:
                # Find the first { and last }
                first = text.find("{")
                last = text.rfind("}")
                if last > first:
                    cand = text[first:last+1]
                    data = json.loads(cand)
                    if "response" in data:
                        data["text"] = data["response"]
                    return data
            except:
                pass

        # 3. Fallback
        clean = re.sub(r'```(json|yaml|toon)?', '', raw_text).replace('```', '').strip()
        return {
            "response": clean,
            "text": clean,
            "suggestions": [],
            "emotion": "neutral"
        }

    def generate_response(self, message, context=None, image=None):
        """Generates a TOON response for the given message."""
        if not self.api_key:
            return {"response": "設定画面でGoogle Gemini APIキーを設定してください。", "emotion": "neutral", "suggestions": []}

        try:
            now = datetime.datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            hour = now.hour
            time_segment = "Night"
            if 5 <= hour < 11: time_segment = "Morning"
            elif 11 <= hour < 16: time_segment = "Daytime"
            elif 16 <= hour < 19: time_segment = "Evening"
            elif 19 <= hour < 23: time_segment = "Night"
            
            base_context = f"Current Time: {now_str} ({time_segment})\n"
            if context:
                base_context += f"{context}\n"
            
            # System Prompt (TOON Requirement)
            system_prompt_add = """
[SYSTEM REMINDER]
Response Format: **TOON (Token-Oriented Object Notation)**
NO JSON. NO Markdown code blocks. Just plain text with indentation.

response:
  text: Your spoken response here. (Quotes and newlines allowed)
emotion: happy
suggestions:
  - Suggestion 1
  - Suggestion 2
  - Suggestion 3
  - Suggestion 4
  - 他の話題について
"""
            
            if image:
                logging.info("Vision request detected")
                vision_instruction = message
                if not message or message.strip() in ["[Screen]", "[Clipboard]", ""]:
                    vision_instruction = "Please analyze this image and describe what you see."
                elif message.strip().startswith("[") and len(message.strip()) < 20: 
                     vision_instruction = f"{message} Please analyze this image."

                full_message = f"[Context]\n{base_context}\n\n[Instruction]\nVision Mode enabled.\n\n[User Request]\n{vision_instruction}\n\n{system_prompt_add}"
                run_config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="text/plain", 
                    tools=[] 
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[full_message, image],
                    config=run_config
                )
            else:
                tools = []
                if self.use_search:
                    tools = [types.Tool(google_search=types.GoogleSearch())]
                
                session = self._get_chat_session(tools=tools)
                full_message = f"[Context/Memory]\n{base_context}\n\n[User Input]\n{message}\n\n{system_prompt_add}"
                
                run_config = None
                if self.use_search:
                    run_config = types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        response_mime_type="text/plain"
                    )

                response = session.send_message(full_message, config=run_config)

            raw_text = response.text

            # Grounding extraction (Simplified for brevity but preserved logic)
            grounding_info = None
            try:
                candidates = getattr(response, 'candidates', [])
                if candidates and hasattr(candidates[0], 'grounding_metadata'):
                    gm = candidates[0].grounding_metadata
                    if gm:
                        queries = list(getattr(gm, 'web_search_queries', []))
                        sources = []
                        chunks = getattr(gm, 'grounding_chunks', [])
                        for chunk in chunks:
                            if hasattr(chunk, 'web') and chunk.web:
                                sources.append({"title": chunk.web.title, "url": chunk.web.uri})
                        if queries or sources:
                            grounding_info = {"queries": queries, "sources": sources}
            except: pass

            result = self._parse_ai_response(raw_text)
            result["grounding_info"] = grounding_info
            return result
            
        except Exception as e:
            logger.error(f"Generation Error: {e}")
            return {"response": f"エラー: {str(e)}", "emotion": "sad", "suggestions": []}

    def generate_proactive_message(self, context=None):
        prompt = "User is idle. Initiate a conversation naturally."
        if context: prompt += f"\nContext: {context}"
        return self.generate_response(prompt)

    def generate_title_summary(self, conversation_text):
        if not self.client: return None
        prompt = f"Generate a short title (max 20 chars) in Japanese for this conversation:\n{conversation_text[:500]}"
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip().replace('"', '')
        except: return None

    def reset_chat(self):
        self.chat_session = None
        self.history = []
