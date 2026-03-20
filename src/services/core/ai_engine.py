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
        self.voice_name = "Aoede" # Default voice
        self.parser = ResponseParser() 
        self.mind_logger = None 
        self.memory_service = None
        
        self.temperature = 0.9
        self.system_instruction = "You are a helpful AI assistant."
        self.use_search = True

    def set_mind_logger(self, callback):
        """思考プロセス（Mind Log）を出力するためのコールバックを設定します。"""
        self.mind_logger = callback

    def set_memory_service(self, service):
        """MemoryServiceを設定します (Learned Facts用)"""
        self.memory_service = service

    def _log_thought(self, thought):
        """内部思考をログに出力します（デスクトップアプリのDebugタブに表示）。"""
        if self.mind_logger:
            self.mind_logger(thought)

    def configure(self, api_key, reasoning_model=None, tts_model=None, voice_name=None, system_instruction=None):
        """
        API設定を初期化または更新します。
        
        Args:
            api_key (str): Google GenAI APIキー
            reasoning_model (str): 推論用モデル名 (例: gemini-2.0-flash)
            tts_model (str): 音声合成用モデル名
            voice_name (str): 音声名 (例: Puck, Charon)
            system_instruction (str): システムプロンプト（ペルソナ設定など）
        """
        self.api_key = api_key
        if reasoning_model: self.reasoning_model = reasoning_model
        if tts_model: self.tts_model = tts_model
        if voice_name: self.voice_name = voice_name
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
            system_instruction=self.system_instruction,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE")
            ]
        )

        contents = [full_prompt]
        if image: 
            contents.append(image)
            self._log_thought(f"👁️ [Vision] Receiving visual input... Analyzing.")

        try:
            # 3. API呼び出し (Standard Chat - No Memory Tools to avoid 400 Error on Pro models)
            # Memory Serviceのツールはメインの会話では使わず、事後分析(Observer)で実行する
            
            # Config再構築
            run_config = types.GenerateContentConfig(
                response_mime_type=mime_type, 
                response_schema=None, 
                tools=tools, # Only Search, no Memory tools here
                temperature=0.9,
                system_instruction=self.system_instruction,
                safety_settings=config.safety_settings
            )
            
            # Initial Request
            response = self.client.models.generate_content(
                model=self.reasoning_model,
                contents=contents,
                config=run_config
            )

            # ★ Handle Function Calls (Loop - Only for Search if enabled)
            while response.function_calls:
                self._log_thought("🛠️ [Tools] Model triggered Function Call...")
                
                contents.append(response.candidates[0].content) 
                
                for fc in response.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args
                    
                    self._log_thought(f"  - Call: {fn_name}({fn_args})")
                    
                    # Execute Search Only
                    tool_result = "Error: Tool execution failed."
                    # (Google Search is handled automatically by SDK usually? 
                    # No, we need to handle it or let SDK handle it? 
                    # If we use `google_search=types.GoogleSearch()`, Gemini SDK handles it AUTOMATICALLY if we use `tools` properly?
                    # The newer `google-genai` SDK with `types.Tool` might handle search automatically on server side?
                    # "Automatic function calling" is enabled if we don't intercept?
                    # The logs said "AFC is enabled".
                    # So we might not need to manually loop for Search.
                    # But if we receive function_calls, we MUST handle them or send them back.
                    # If AFC is enabled, we shouldn't see function_calls in response unless mode is ANY?
                    # We'll assume for now we just handle manual calls if any (but Search is server-side usually).
                    
                    # If it IS a manual tool call we missed:
                    tool_result = "Function executed."

                    self._log_thought(f"  - Result: {tool_result}")
                    
                    tool_output = types.Part.from_function_response(
                        name=fn_name,
                        response={"result": tool_result}
                    )
                    
                    tool_content = types.Content(
                        role="tool",
                        parts=[tool_output]
                    )
                    contents.append(tool_content)

                # Send back
                response = self.client.models.generate_content(
                    model=self.reasoning_model,
                    contents=contents,
                    config=run_config
                )

            # 4. ★RAG（検索結果）のログ出力
            grounding = self._extract_grounding(response)
            if grounding and grounding.get("sources"):
                self._log_thought(f"🌍 [RAG] Accessed {len(grounding['sources'])} sources.")
                for src in grounding['sources'][:3]:
                    self._log_thought(f"  - {src['title']}")

            # 5. レスポンスのパース
            data = {}
            text_result = ""
            try:
                text_result = response.text
            except ValueError:
                self._log_thought("⚠️ [Safety] Response blocked by filters.")
                text_result = ""

            if text_result:
                data = self.parser.parse(text_result)
            else:
                 data = {"response": "（言葉に詰まっているようです……）", "emotion": "sad", "suggestions": []}

            # 6. 思考と感情のログ出力
            if data.get("thought"):
                self._log_thought(f"💭 {data['thought']}")
            if data.get("emotion"):
                self._log_thought(f"🎭 [Expression] {data['emotion']}")
            
            # ★ 7. 事後学習 (Async Observer)
            # 会話が終わった後、裏で「記憶すべき事実」がないかチェックする
            if self.memory_service and text_result:
                import threading
                threading.Thread(
                    target=self._check_and_learn_facts, 
                    args=(message, data["response"]), 
                    daemon=True
                ).start()

            # 8. 正規化データの返却
            return {
                "text": data["response"],
                "emotion": data["emotion"],
                "suggestions": data["suggestions"],
                "grounding_info": grounding,
                "action_command": data.get("action_command", "")
            }

        except Exception as e:
            logger.error(f"Gen Error: {e}")
            return {"text": f"エラーが発生しました: {str(e)}", "emotion": "sad", "suggestions": []}

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
        if not text or "Error" in text or "エラー" in text:
            logger.warning(f"TTS Blocked (Error Content): {text[:20]}...")
            return None

        try:
            # 0. Text Cleaning (User Recommendation)
            import re
            clean_text = text.replace('〜', 'ー').replace('～', 'ー')
            clean_text = clean_text.replace('…', '。').replace('♪', '。')
            clean_text = re.sub(r'[^\w\sぁ-んァ-ヶー一-龠、。！？]', '', clean_text)
            clean_text = clean_text.strip()
            
            if not clean_text:
                logger.warning("TTS: Input text became empty after cleaning.")
                return None

            # 1. API Call with Retry Loop
            max_retries = 3
            import time
            
            for attempt in range(max_retries):
                try:
                    # TTS専用モデルのためのクリーンリクエスト（500エラー回避）
                    config = types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=self.voice_name
                                )
                            )
                        ),
                        automatic_function_calling=None,
                        temperature=None,
                        top_p=None,
                        top_k=None
                    )
                    actual_model = f"models/{self.tts_model}" if not self.tts_model.startswith("models/") else self.tts_model
                    return self.client.models.generate_content(
                        model=actual_model,
                        contents=[clean_text], 
                        config=config
                    )
                except Exception as api_error:
                    error_msg = str(api_error)
                    is_retryable = any(code in error_msg for code in ["500", "503", "429", "INTERNAL", "UNAVAILABLE", "ResourceExhausted"])
                    
                    if is_retryable and attempt < max_retries - 1:
                        delay = 1.0 * (2 ** attempt)
                        logger.warning(f"AIEngine: Gemini TTS transient error (Attempt {attempt+1}/{max_retries}): {error_msg}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        raise api_error

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

    def _check_and_learn_facts(self, user_text, ai_text):
        """
        [Async Observer]
        会話の内容を分析し、Learned Facts（記憶すべき事実）があれば save_learned_fact を呼び出す。
        メインの会話生成とは別のモデル（Tool対応モデル）を使用する。
        """
        if not self.client or not self.memory_service:
            return

        try:
            # Tool-capable model (Gemini 2.0 Flash is reliable for tools)
            observer_model = "gemini-2.0-flash-exp" 

            prompt = f"""
[Task]
Analyze the conversation below. 
If the USER provided new information about themselves (preferences, profile) or corrected the AI's knowledge, 
IMMEDIATELY call the `save_learned_fact` tool to save it.

[Conversation]
User: {user_text}
AI: {ai_text}

[Constraint]
- Only save facts explicitly stated or strongly implied by the user.
- If no relevent facts are found, do nothing (output minimal text).
- IGNORE facts already known or trivial context.
"""
            tools = [self.memory_service.save_learned_fact]
            
            config = types.GenerateContentConfig(
                tools=tools,
                temperature=0.1 # Low temperature for factual extraction
            )
            
            # self._log_thought(f"🧠 [Observer] Checking for learned facts...")

            response = self.client.models.generate_content(
                model=observer_model,
                contents=prompt,
                config=config
            )

            # Handle Function Calls
            if response.function_calls:
                for fc in response.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args
                    
                    self._log_thought(f"📝 [Memory] Learning new fact via {fn_name}: {fn_args}")
                    
                    if fn_name == "save_learned_fact":
                        try:
                            res = self.memory_service.save_learned_fact(**fn_args)
                            self._log_thought(f"✅ [Memory] Saved: {res}")
                        except Exception as e:
                            self._log_thought(f"❌ [Memory] Save Failed: {e}")

        except Exception as e:
            # Observer failure should not impact main thread
            # logger.error(f"Observer Error: {e}")
            pass


    def transform_query(self, user_question, chat_history):
        """
        Retrieval-Augmented Generation (RAG) 向けのクエリ変換を行います。
        直前の会話履歴を踏まえ、ユーザーの質問を「検索に適した完全な質問文」に書き換えます。
        """
        if not self.client: return user_question # Fallback

        # Lightweight model for this specific NLP task
        model_name = "gemini-2.5-flash" 

        prompt = f"""
# Role
あなたは会話の文脈を理解し、検索クエリを最適化するアシスタントです。
ユーザーは直前の会話の流れを踏まえて短い質問（主語の省略など）をすることがあります。
あなたの仕事は、以下の「会話履歴」と「最新の質問」を読み解き、**検索エンジンが正しく情報を探せるように、最新の質問を具体的かつ独立した質問文（Standalone Question）に書き換えること**です。

# Constraints
- 元の質問の意図を変えないでください。
- 「それ」「あれ」「この」などの指示語がある場合は、会話履歴から具体的な名詞を特定して置き換えてください。
- 主語が省略されている場合は、会話履歴から現在のトピック（話題）を特定し、主語を補ってください。
- 回答は**書き換えた質問文のみ**を出力してください。余計な挨拶や説明は不要です。

# Examples
History:
User: 光るキノコの栽培キットってある？
AI: はい、ヤコウタケ栽培キットなどが販売されています。

Current Input:
User: 寿命はどれくらい？

Rewritten Query:
ヤコウタケ栽培キットの寿命はどれくらいですか？
----------------
History:
User: Pythonのコードがエラーになるんだ。
AI: どのようなエラーですか？
User: "IndexError: list index out of range" って出る。

Current Input:
User: どうやって直せばいい？

Rewritten Query:
Pythonの "IndexError: list index out of range" の直し方は？
----------------

# Conversation History
{chat_history}

# Current Input
{user_question}

# Rewritten Query:
"""
        try:
            # Use raw generate_content for speed
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1) # Low temp for precision
            )
            rewritten = response.text.strip()
            self._log_thought(f"🔄 [Query Transform] '{user_question}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"Query Transform Failed: {e}")
            return user_question

    def plan_os_action(self, instruction, context=None):
        """
        [OS Control] 自然言語の指示を `pyautogui` コードに変換します。
        Args:
            instruction (str): ユーザーの指示
            context (str, optional): 過去の失敗やリトライ時の補足情報
        Returns:
            dict: {"code": "...", "explanation": "..."}
        """
        if not self.client: return None

        prompt = f"""
# Role
あなたはWindows OS操作のエキスパートです。
ユーザーの指示に従い、`pyautogui` や `win32_input` を使用してタスクを実行するPythonコードを生成してください。

# User Instruction
{instruction}

# Context (Experience & Retry Info)
{context or "特になし"}

# Requirements
- Output MUST be valid Python code.
- Use `pyautogui` library for basic keys (enter, esc, etc).
- **CRITICAL: NO TAB NAVIGATION**: Do NOT use `pyautogui.press('tab')` for selecting items. It is unreliable.
- **CRITICAL: USE VISION CLICK**: To select or click ANYTHING (links, buttons, videos), use `vision_click('description')`.
    - Example: `vision_click('Top video thumbnail')`, `vision_click('Search Button')`
- **Text Input**: Use `safe_type('text')`.
- **Browser**: Use `open_browser('url')`.
- **Discord**:
    - `discord_navigate('channel_name')`: Use Quick Switcher (Ctrl+K) to jump to channel per user request.
    - `discord_send_message('message')`: Send message (Auto-Activates active chat).
- **Refinement**: If 'Context' contains failure info, CHANGE the approach.

# Output Format: JSON
{{
    "code": "open_browser('https://youtube.com'); time.sleep(5); vision_click('Top left video thumbnail');",
    "explanation": "YouTubeを開き、ロードを待ってから、一番左上の動画を目視でクリックします。"
}}

# Example 1: Search and Click
Instruction: "Open YouTube and click the first video"
Code:
open_browser('https://www.youtube.com')
time.sleep(5) # Wait for load!
vision_click('First video thumbnail in the list')

# Example 2: Discord Message
Instruction: "Discordで開発チャンネルに「お疲れ様」と送って"
Code:
discord_navigate('開発')
time.sleep(1)
discord_send_message('お疲れ様！')
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview", # Intelligent enough for coding
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Plan OS Action Failed: {e}")
            return None

    def verify_action_success(self, instruction, before_img, after_img):
        """
        [OS Control] Visionを使って操作の成否を判定します。
        Returns:
            dict: {"success": bool, "reason": "Notepad appeared"}
        """
        if not self.client: return {"success": False, "reason": "No Client"}

        prompt = f"""
# Role
あなたはUIテストの判定員です。
OS操作の「実行前」と「実行後」の画像を見て、ユーザーの指示が達成されたか判断してください。

# Instruction
{instruction}

# Output Format (JSON)
{{
    "success": true/false,
    "reason": "詳細な理由（例：メモ帳のウィンドウが表示されているため）"
}}
"""
        try:
            # Check inputs
            if not before_img or not after_img:
                return {"success": False, "reason": "Images missing"}

            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[prompt, "Before:", before_img, "After:", after_img],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Verify Action Failed: {e}")
            return {"success": False, "reason": str(e)}

