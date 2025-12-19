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
        self.history = [] # Local history storage if needed, or rely on chat_session object?
        # New SDK chat_session (client.chats.create) maintains its own history.
        
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
                logging.info(f"AIEngine configured with new SDK. Model: {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to configure Gemini Client: {e}")

    def set_system_prompt(self, prompt_text):
        """Updates the system prompt and resets the session."""
        logging.info("Updating System Prompt from Persona.")
        self.system_instruction = prompt_text
        self.chat_session = None

    def _get_chat_session(self, tools=None):
        """Initializes or returns the chat session."""
        if self.chat_session is None:
            if not self.client:
                raise ValueError("Client not initialized. Call configure() first.")

            # Config
            # Note: With Grounding, strict JSON schema might conflict or be unsupported on 2.5-flash-lite currently.
            # We revert to text/plain and rely on prompt instruction for JSON.
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

    def _parse_ai_response(self, raw_text: str) -> dict:
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
        # (AIがコードブロックの外に余計な挨拶などを書いた場合への対策)
        if "{" in text:
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if last_brace > first_brace:
                text = text[first_brace : last_brace + 1]

        # 3. JSONパースの試行
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logging.warn(f"[AI Engine] JSON Parse Error: {e}")
            logging.warn(f"[AI Engine] Failed Text: {raw_text[:100]}...")
            
            # 4. 最終手段: パース失敗時は、テキスト全体をresponseとして扱う（生JSONを見せるよりマシ）
            # ただし、元の raw_text ではなく、クリーニング済みの text を使う
            # Markdownタグ (```) が残っている場合は除去
            info_text = text.replace("```json", "").replace("```", "").strip()
            
            return {
                "response": info_text, # ここが重要。タグが消えた状態のテキストを出す
                "suggestions": [],
                "emotion": "neutral"
            }


    def generate_response(self, message, context=None, image=None):
        """Generates a JSON response for the given message."""
        if not self.api_key:
            return {"response": "設定画面でGoogle Gemini APIキーを設定してください。", "emotion": "neutral", "suggestions": []}

        try:
            # Context Construction (Shared)
            now = datetime.datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Simple Time Segment
            hour = now.hour
            time_segment = "Night"
            if 5 <= hour < 11: time_segment = "Morning"
            elif 11 <= hour < 16: time_segment = "Daytime"
            elif 16 <= hour < 19: time_segment = "Evening"
            elif 19 <= hour < 23: time_segment = "Night"
            
            base_context = f"Current Time: {now_str} ({time_segment})\n"
            if context:
                base_context += f"{context}\n"
            
            # System Prompt (JSON Requirement)
            system_prompt_add = """
[SYSTEM REMINDER]
JSON Output Required! 
Format: {"response": "string", "emotion": "string", "suggestions": ["string", "string"]}
Key "suggestions": Provide 2-3 short, natural Japanese response options.
"""
            
            # --- BRANCH: VISION MODE (Stateless) ---
            if image:
                logging.info("Vision request detected: Using stateless generate_content")
                
                # Check for empty or tag-only message
                # If message is empty or just standard tags, give a default instruction
                vision_instruction = message
                if not message or message.strip() in ["[Screen]", "[Clipboard]", ""]:
                    vision_instruction = "Please analyze this image and describe what you see."
                elif message.strip().startswith("[") and len(message.strip()) < 20: 
                     # Heuristic: If short tag-like message, treat as needing description
                     vision_instruction = f"{message} Please analyze this image."

                # Vision Prompt with Strong Override
                full_message = f"""
[Context]
{base_context}

[Instruction]
You are currently in **Vision Mode**. You CAN see the attached image.
Ignore any previous instructions stating you cannot see images.
Please answer the user's request based on the image.

[User Request]
{vision_instruction}

{system_prompt_add}
"""
                # Disable tools (Search) for Vision
                run_config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="text/plain", 
                    tools=[] 
                )
                
                # Stateless Generation
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[full_message, image],
                    config=run_config
                )
                
            # --- BRANCH: CHAT MODE (Stateful / Grounding) ---
            else:
                # Google Search Toolの設定を確認
                tools = []
                if self.use_search: # もし検索機能フラグがあれば
                    tools = [types.Tool(google_search=types.GoogleSearch())]
                
                session = self._get_chat_session(tools=tools)

                full_message = f"""
[Context/Memory]
{base_context}

[User Input]
{message}

{system_prompt_add}
"""

                # Generate content
                # Tools Config for this turn
                run_config = None
                if self.use_search:
                     # Explicitly pass tools in config to ensure availability
                     # and override any session defaults if needed.
                     run_config = types.GenerateContentConfig(
                         tools=[types.Tool(google_search=types.GoogleSearch())],
                         response_mime_type="text/plain"
                     )

                response = session.send_message(
                    full_message,
                    config=run_config
                )

            # Common Response Parsing
            raw_text = response.text
            logging.info(f"raw_text: {raw_text}")

            # ★ Grounding (Search) Info Extraction
            grounding_info = None
            try:
                # DEBUG: Inspect the response object structure
                logging.info(f"[DEBUG] Response Type: {type(response)}")
                logging.info(f"[DEBUG] Response Candidates: {response.candidates if hasattr(response, 'candidates') else 'No candidates'}")
                if hasattr(response, 'candidates') and response.candidates:
                    c0 = response.candidates[0]
                    logging.info(f"[DEBUG] Candidate 0 vars: {vars(c0)}")
                    if hasattr(c0, 'grounding_metadata'):
                        logging.info(f"[DEBUG] Grounding Metadata found: {c0.grounding_metadata}")
                    else:
                        logging.info("[DEBUG] No grounding_metadata in Candidate 0")

                # 安全にメタデータにアクセス
                candidates = getattr(response, 'candidates', [])
                if candidates and hasattr(candidates[0], 'grounding_metadata'):
                    gm = candidates[0].grounding_metadata
                    
                    if gm: # メタデータ自体がNoneでないか確認
                        # 1. 検索クエリの取得
                        queries = []
                        # hasattrだけでなく、中身がNoneでないことも確認する
                        if hasattr(gm, 'web_search_queries') and gm.web_search_queries:
                            queries = [q for q in gm.web_search_queries]
                        
                        # 2. 参照ソースの取得
                        sources = []
                        if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                            for chunk in gm.grounding_chunks:
                                # web情報を持っているか確認
                                if hasattr(chunk, 'web') and chunk.web:
                                    sources.append({
                                        "title": chunk.web.title,
                                        "url": chunk.web.uri
                                    })
                        
                        # データがあればセット
                        if queries or sources:
                            grounding_info = {
                                "queries": queries,
                                "sources": sources
                            }
                            logging.info(f"[Grounding] Found info: {grounding_info}")

            except Exception as e:
                logging.warning(f"[Grounding] Extract Error: {e}")

            # 3. Explicit Logging for No-Search Scenario
            if grounding_info is None and self.use_search:
                logging.info("[Grounding] No search performed by AI (Dynamic Retrieval decision).")
                # Optional: Pass this state to frontend so it's not just "empty"
                grounding_info = {
                    "queries": [],
                    "sources": [],
                    "status": "No search performed (Knowledge used)"
                }

            # レスポンスの構築
            result = self._parse_ai_response(raw_text)
            
            # Frontend expects 'text' key (based on user snippet and index.ts)
            # Map 'response' from JSON to 'text' for frontend compatibility
            if "response" in result:
                result["text"] = result["response"]
            
            result["grounding_info"] = grounding_info
            return result
            
        except Exception as e:
            logging.error(f"Generation Error: {e}")
            return {"response": f"エラー: {str(e)}", "emotion": "sad", "suggestions": []}

    def generate_proactive_message(self, context=None):
        """Generates a proactive message (Active Talk)."""
        prompt = "User is idle. Initiate a conversation naturally. Check the time and suggest a topic."
        if context:
            prompt += f"\nContext: {context}"
        return self.generate_response(prompt)

    def generate_title_summary(self, conversation_text):
        """会話履歴から短いタイトルを生成する"""
        if not self.client: # client check instead of model
            return None
            
        prompt = f"""
Task: Generate a very short title (max 20 chars) for the following conversation in Japanese.
- Ignore system prompts like [Situation] or [User Profile].
- Focus on the main topic.
- Output ONLY the title text. No quotes.

Conversation:
{conversation_text[:1000]} 
"""
        # API呼び出し (generate_content)
        try:
            # client.models.generate_content using self.model_name
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            title = response.text.strip().replace('"', '').replace('「', '').replace('」', '')
            # Newlines removal just in case
            title = title.replace('\n', ' ')
            return title
        except Exception as e:
            logging.error(f"[AIEngine] Title generation failed: {e}")
            return None

    def reset_chat(self):
        self.chat_session = None
        self.history = []

    def generate_content(self, prompt):
        """Raw content generation utility."""
        if not self.client: return None
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logging.error(f"Raw Gen Error: {e}")
            return None
