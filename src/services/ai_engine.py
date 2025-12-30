import logging
import datetime
import json
from google import genai
from google.genai import types
from src.core.response_parser import ResponseParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    """
    Google GenAI SDK (Gemini API) を利用して、テキスト生成、マルチモーダル入力、
    RAG（Grounding）、ツール利用などを統括するクラスです。
    """
    def __init__(self):
        self.api_key = None
        self.client = None
        self.reasoning_model = "gemini-3-flash-preview" 
        self.tts_model = "gemini-2.5-flash-preview-tts"
        self.parser = ResponseParser() 
        self.mind_logger = None 
        
        self.temperature = 0.9
        self.system_instruction = "You are a helpful AI assistant."
        self.use_search = True

    def set_mind_logger(self, callback):
        """思考プロセス（Mind Log）を出力するためのコールバックを設定します。"""
        self.mind_logger = callback

    def _log_thought(self, thought):
        """内部思考をログに出力します（デスクトップアプリのDebugタブに表示）。"""
        if self.mind_logger:
            self.mind_logger(thought)

    def configure(self, api_key, reasoning_model=None, tts_model=None, system_instruction=None):
        """
        API設定を初期化または更新します。
        
        Args:
            api_key (str): Google GenAI APIキー
            reasoning_model (str): 推論用モデル名 (例: gemini-2.0-flash)
            tts_model (str): 音声合成用モデル名
            system_instruction (str): システムプロンプト（ペルソナ設定など）
        """
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
        """
        ユーザーの入力に対する応答を生成します。
        
        Args:
            message (str): ユーザーからのメッセージ
            context (str, optional): 会話の文脈情報
            image (Any, optional): 画像データ（マルチモーダル入力用）
        
        Returns:
            dict: 応答テキスト、感情、推奨アクションなどを含む辞書
        """
        if not self.client:
            return {"text": "API Key Error", "emotion": "sad", "suggestions": []}

        # 1. プロンプト構築 (Strict JSON対応)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_prompt = f"""
[Current Time] {now}
[Context] {context or ''}
[User Input] {message}

[CRITICAL URL RULE]
1. NEVER edit, guess, or construct URLs.
2. ONLY use the exact `url` string provided by the Google Search tool.
3. DO NOT update years/dates in URLs to match the current system time (e.g. do not change /2024/ to /2025/).
4. If you are unsure of a link's validity, do not show it.

[LANGUAGE CONSTRAINT]
Your "thought" and "response" MUST be in JAPANESE (日本語).
Even if the system instructions are in English, the FINAL OUTPUT for the user MUST be Japanese.

[SYSTEM OUTPUT REQUIREMENT]
You MUST output a valid JSON object. NO markdown, NO code blocks, NO preamble.
Format:
{{
    "thought": "Internal monologue...",
    "response": "Response to user...",
    "emotion": "neutral/happy/sad/...",
    "suggestions": ["sugg1", "sugg2", "sugg3"],
    "action_command": ""
}}
"""
        # 2. 設定構築 (JSON Mode)
        # 検索ツールが有効な場合は設定
        tools = [types.Tool(google_search=types.GoogleSearch())] if self.use_search else []

        # API制約: Tool利用時は response_mime_type: 'application/json' がサポートされない場合があるためテキストモードを使用
        mime_type = "application/json"
        if tools:
            mime_type = "text/plain"

        config = types.GenerateContentConfig(
            response_mime_type=mime_type, 
            response_schema=None, 
            tools=tools,
            temperature=0.9,
            system_instruction=self.system_instruction
        )

        contents = [full_prompt]
        if image: 
            contents.append(image)
            self._log_thought(f"👁️ [Vision] Receiving visual input... Analyzing.")

        try:
            # 3. API呼び出し
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=config
            )

            # 4. ★RAG（検索結果）のログ出力 (最優先)
            grounding = self._extract_grounding(response)
            if grounding and grounding.get("sources"):
                self._log_thought(f"🌍 [RAG] Accessed {len(grounding['sources'])} sources.")
                for src in grounding['sources'][:3]:
                    self._log_thought(f"  - {src['title']}")

            # 5. レスポンスのパース (ResponseParser使用)
            data = {}
            if response.text:
                data = self.parser.parse(response.text)
            else:
                 data = {"response": "", "emotion": "error", "suggestions": []}

            # 6. 思考と感情のログ出力
            if data.get("thought"):
                self._log_thought(f"💭 {data['thought']}")
            if data.get("emotion"):
                self._log_thought(f"🎭 [Expression] {data['emotion']}")

            # 7. 正規化データの返却
            return {
                "text": data["response"],
                "emotion": data["emotion"],
                "suggestions": data["suggestions"],
                "grounding_info": grounding,
                "action_command": data.get("action_command", "")
            }

        except Exception as e:
            logger.error(f"Gen Error: {e}")
            return {"text": "エラーが発生しました。", "emotion": "sad", "suggestions": []}

    def _extract_grounding(self, response):
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

    def generate_tts_with_gemini(self, text):
        """TTS生成 (テキストのみ渡す)"""
        try:
            config = types.GenerateContentConfig(response_modalities=["AUDIO"])
            return self.client.models.generate_content(
                model=self.tts_model,
                contents=text, 
                config=config
            )
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return None

    def analyze_youtube_video(self, video_url, user_message=None):
        """
        YouTube動画の内容を分析し、ユーザーと一緒に視聴しているかのようなコメントを生成します。
        Geminiのネイティブマルチモーダル機能を使用します。
        
        Args:
            video_url (str): YouTube動画のURL
            user_message (str, optional): ユーザーからのコメント
        """
        if not self.client:
            return {"text": "API Key error.", "emotion": "sad", "suggestions": []}

        logger.info(f"[System] Native Video Analysis Started: {video_url}")
        self._log_thought(f"📺 [System] Native Video Analysis Started: {video_url}")
        
        # 通常の応答生成に似ていますが、動画分析用に調整されています
        user_input = user_message if user_message else "この動画、一緒に見よう？"
        
        prompt_text = f"""
User says: '{user_input}'
Instruction: Analyze the video visuals and audio. Share your thoughts in JAPANESE (日本語).
[SYSTEM OUTPUT REQUIREMENT]
You MUST output a valid JSON object.
Format:
{{
    "thought": "Internal reasoning...",
    "response": "Response to user...",
    "emotion": "neutral",
    "suggestions": [],
    "action_command": ""
}}
"""
        try:
            video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/*")
            contents = [video_part, prompt_text]
            
            tools = [types.Tool(google_search=types.GoogleSearch())]
            
            # API制約: Tool利用時は response_mime_type: 'application/json' がサポートされないためテキストモードを使用
            # ここでは常に検索ツールが有効
            run_config = types.GenerateContentConfig(
                tools=tools,
                response_mime_type="text/plain",
                temperature=self.temperature
            )
            
            self._log_thought(f"🧠 [Mind] Analyzing video frames & audio context...\nTarget: {video_url}")

            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=run_config
            )
            
            # RAG情報の抽出
            grounding = self._extract_grounding(response)
            
            # パース
            data = {}
            if response.text:
                data = self.parser.parse(response.text)
                
            ai_thought = data.get("thought", "")
            if ai_thought:
                 self._log_thought(f"👁️ [Vision] {ai_thought}")

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

    def generate_proactive_message(self, context=None):
        prompt = "User is idle. Initiate a conversation naturally. Suggest a topic for the user."
        if context: prompt += f"\nContext: {context}"
        prompt += "\n[Language Constraint] OUTPUT MUST BE IN JAPANESE (日本語で話してください)."
        return self.generate_response(prompt)

    def generate_raw_response(self, prompt, model=None):
        """Generates response without Chat JSON formatting/parser."""
        if not self.client:
             logger.error("Client not initialized.")
             return None
        
        try:
            target_model = model or self.reasoning_model
            response = self.client.models.generate_content(
                model=target_model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Raw Gen Error: {e}")
            return None

    def generate_title_summary(self, conversation_text):
        if not self.client: return None
        # Title doesn't need strict JSON, just text
        prompt = f"Generate a short title (max 20 chars) in Japanese for this conversation:\n{conversation_text[:500]}"
        try:
            response = self.client.models.generate_content(model=self.reasoning_model, contents=prompt)
            return response.text.strip().replace('"', '')
        except: return None
