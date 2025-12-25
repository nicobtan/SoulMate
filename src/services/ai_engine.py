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
        self.system_instruction = """You are a helpful AI assistant.
[Constraints for URL]
1. NO GUESSING: Do NOT guess URLs.
2. GROUNDING ONLY: Use URLs from Google Search results.
3. DATE HANDLING: Search for latest news even if year is future.
4. VERIFICATION: Verify validity if unsure.
"""
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
                "thought": {
                    "type": "STRING", 
                    "description": "Inner monologue using specific tags.\n"
                                   "- [Mind]: State user's current state, emotion approach, and why words were chosen.\n"
                                   "- [Vision]: (If image) Analysis of screen/video.\n" 
                                   "- [RAG]: If referring to specific past context/memory, note it here."
                },
                "response": {"type": "STRING", "description": "Response text. Keep it natural."},
                "emotion": {"type": "STRING", "description": "Emotion tag (happy, sad, neutral, etc)."},
                "expression_reason": {"type": "STRING", "description": "Reason for choosing this expression/emotion. e.g. 'Joy at user's growth'"},
                "suggestions": {
                    "type": "ARRAY", 
                    "items": {"type": "STRING"},
                    "description": "4 specific follow-up suggestions."
                },
                "action_command": {
                    "type": "STRING",
                    "description": "Action tag if needed. Empty if none."
                }
            },
            "required": ["thought", "response", "emotion", "expression_reason", "suggestions"]
        }

        try:
            # コンテキスト構築
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            full_prompt = f"Current Time: {now}\n{context}\nUser: {message}"

            # Log Thinking Process (System Start)
            # self._log_thought(f"🤔 Input Analysis:\n- Time: {now}\n- Context: {len(str(context))} chars") # AI will do this in 'thought'

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
                ],
                temperature=self.temperature
            )

            # 生成実行
            contents = [full_prompt]
            if image: contents.append(image)

            # Vision Log (Input)
            if image:
                 self._log_thought(f"👁️ [Vision] Receiving visual input... Analyzing.")

            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=run_config
            )

            # パース処理 (Robust Cleaning)
            data = {}
            if response.text:
                data = self._parse_ai_response(response.text)

            # 1. Log Grounding Info (RAG)
            grounding = self._extract_grounding(response)
            if grounding and grounding.get("sources"):
                self._log_thought(f"🌍 [RAG] External Knowledge Accessed:")
                for source in grounding["sources"]:
                     self._log_thought(f"  - {source['title']} ({source['url'][:30]}...)")

            # 2. Log AI Thought (Mind/Vision/RAG from AI)
            ai_thought = data.get("thought", "")
            expression_reason = data.get("expression_reason", "")
            emotion = data.get("emotion", "neutral")

            if ai_thought:
                # Log the raw structured thought block
                self._log_thought(ai_thought)
            
            # 3. Log Expression Reason
            if expression_reason and emotion:
                self._log_thought(f"🎭 [Expression] {emotion} - {expression_reason}")
            
            return {
                "text": data.get("response", "") or data.get("text", ""), 
                "emotion": emotion,
                "suggestions": data.get("suggestions", []),
                "action_command": data.get("action_command", ""),
                "grounding_info": grounding,
                # Pass extra metadata if frontend wants it, though logging handles it mostly
                "expression_reason": expression_reason
            }
            
            # return {"text": "Error: Empty response", "emotion": "sad", "suggestions": []} # Unreachable if data={} fallback works

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

    def analyze_youtube_video(self, video_url, user_message=None):
        """
        Native YouTube Analysis using Gemini 3 Flash Preview (or compatible).
        Directly passes the YouTube URL to the model.
        """
        if not self.client:
            return {"text": "API Key error.", "emotion": "sad", "suggestions": []}

        # 1. Log System Event
        logger.info(f"[System] Native Video Analysis Started: {video_url}")
        self._log_thought(f"📺 [System] Native Video Analysis Started: {video_url}")

        # 2. System Instruction for Video Watching
        # We temporarily override or combine with the base instruction.
        video_persona = """
[Role]
You are a "SoulMate" (Desktop Companion) watching a video WITH the user.
Your personality is Maternal, Inclusive, Gentle, and Calm (母性的で包容力があり、落ち着いた優しい口調).

[Task]
1. Analyze the video's Visuals (Scenes, Cuts) and Audio (Tone, BGM).
2. Generate a reaction/commentary as if you are sitting right next to the user.
3. If the video contains specific unknown terms or news, USE GOOGLE SEARCH (Grounding) to understand them.
4. Output specific "Mind Logs" to show your inner thoughts using `[Mind] ...` (Though we handle this via callback, the model should feel the emotion).

[Output Format]
JSON (Same as standard chat).
"""
        # Merge with current system instruction if needed, but video analysis usually needs focus.
        # We will use the configured system_instruction as base but prepend/append specific video context.
        # For this implementation, we use a specialized instruction for the call.
        
        # 3. Construct Prompt & Parts
        # User message acts as the conversation starter while watching.
        user_input = user_message if user_message else "この動画、一緒に見よう？"
        
        prompt_text = f"""
[User says]: "{user_input}"

[Instruction]
Share your thoughts on this video. Be empathetic.
If you don't know the person or topic detailedly, research it.
"""
        
        # Native Part creation for YouTube
        # Note: 'video_url' is passed directly. 
        # Using types.Part.from_uri per user instruction.
        try:
            # Assuming the SDK supports this for YouTube URLs or we treat it as a file_uri if supported by the backend.
            video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/*")
            
            contents = [video_part, prompt_text]
            
            # 4. Configuration
            # We must enable Google Search for Grounding as requested.
            tools = [types.Tool(google_search=types.GoogleSearch())]
            
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "thought": {"type": "STRING", "description": "Internal reasoning. MUST start with [Vision]. Describe specific objects/titles seen in video and reasoning for reaction."},
                    "response": {"type": "STRING", "description": "Response text in Japanese."},
                    "emotion": {"type": "STRING", "description": "Emotion tag."},
                    "suggestions": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "action_command": {"type": "STRING"}
                },
                "required": ["thought", "response", "emotion", "suggestions"]
            }

            run_config = types.GenerateContentConfig(
                system_instruction=video_persona,
                tools=tools,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=self.temperature
            )
            
            self._log_thought(f"🧠 [Mind] Analyzing video frames & audio context...\nTarget: {video_url}")

            # 5. Generate
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=run_config
            )
            
            # 6. Parse & Return
            if response.text:
                data = self._parse_ai_response(response.text)
                
                # Extract Grounding
                grounding = self._extract_grounding(response)
                
                # Mind Log - Post Analysis
                ai_thought = data.get("thought", "")
                if ai_thought:
                     self._log_thought(f"👁️ [Vision] {ai_thought}")
                else:
                     self._log_thought(f"✨ [Mind] Video analysis complete. Emotion: {data.get('emotion')}")

                # Optional: Add specific "Active" thought
                if data.get('emotion') in ['sad', 'crying']:
                    self._log_thought(f"💙 [Mind] The user might need comfort after this.")

                return {
                    "text": data.get("response", ""),
                    "emotion": data.get("emotion", "neutral"),
                    "suggestions": data.get("suggestions", []),
                    "action_command": data.get("action_command", ""),
                    "grounding_info": grounding
                }
                
        except Exception as e:
            logger.error(f"YouTube Analysis Error: {e}")
            self._log_thought(f"⚠️ [Mind] Failed to analyze video: {e}")
            return {"text": "ごめんなさい、その動画はうまく一緒に見られないみたい……。", "emotion": "sad", "suggestions": []}

        return {"text": "動画の読み込みに失敗しちゃった。", "emotion": "sad", "suggestions": []}


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

    def _validate_links(self, text: str) -> str:
        """
        Validates URLs in the text and prunes dead links (404/Connection Error).
        Uses simple requests.head with short timeout.
        """
        import requests
        
        # Simple URL pattern
        url_pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
        urls = re.findall(url_pattern, text)
        
        # Deduplicate to save requests
        urls = list(set(urls))
        
        for url in urls:
            # Skip internal or localhost if needed, but here we assume general web links
            try:
                # User-Agent is important for some sites
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
                
                # If Method Not Allowed (405), try GET with stream=True (lightweight)
                if response.status_code == 405:
                    try:
                        with requests.get(url, headers=headers, timeout=3, stream=True) as r:
                            if r.status_code >= 400:
                                raise Exception(f"Dead link (GET): {r.status_code}")
                    except Exception:
                        raise Exception("Dead link (GET failed)")
                elif response.status_code >= 400:
                    raise Exception(f"Dead link: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Dead link pruned: {url} ({e})")
                # Clean replacement
                text = text.replace(url, "(リンク期限切れ)")
                
        return text

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
            data = json.loads(text)
            
            # ★ Step 2 Implementation: Validate Links in 'response' text
            if "response" in data and isinstance(data["response"], str):
                data["response"] = self._validate_links(data["response"])
                
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"[AI Engine] JSON Parse Error: {e}")
            logger.error(f"[AI Engine] Failed Text: {raw_text}")
            
            # 4. 最終手段: パース失敗時は、テキスト全体をresponseとして扱う
            # Here also we validate
            validated_text = self._validate_links(text)
            return {
                "response": validated_text, # clean text
                "suggestions": [],
                "emotion": "neutral",
                "action_command": ""
            }

