import os
import threading
import random
import webbrowser
import re
import re
import json
import base64
from .base import BaseApiMixin
# from .json_helper import _extract_json_from_text # TOON化により不要
from PIL import ImageGrab
from src.services.content.topic_selector import TopicSelector
from src.services.external.url_validator import UrlValidator
from src.services.content.affection_manager import AffectionManager
from src.services.vision.vision_service import vision_service

class ChatApiMixin(BaseApiMixin):
    """
    チャット機能を提供するMixin。
    Apiクラス（デスクトップ）およびHeadlessApiクラス（サーバー）に継承され、
    共通のチャットロジック（応答生成、ログ記録、TTS呼び出し）を提供します。
    """
    
    def initialize_persona(self, persona_file="lena.yaml"):
        """初期化処理 (文章量調整対応版)"""
        
        # 1. 設定の読み込み
        length_mode = "standard"
        if self._config_manager:
            # 設定キー 'chat_length_mode' を取得 (デフォルトは standard)
            length_mode = self._config_manager.get('chat_length_mode', 'standard')

        # 2. モード別の指示プロンプト定義
        length_instruction = ""
        if length_mode == "concise": # 簡潔
            length_instruction = """
[LENGTH CONSTRAINT]
Keep your response concise and to the point. 
Avoid long explanations or filler words. 
Limit response to 2-3 sentences max.
"""
        elif length_mode == "short": # 短文
            length_instruction = """
[LENGTH CONSTRAINT]
Keep your response EXTREMELY short.
Use only a single sentence or a short phrase (max 20-30 characters).
Be snappy and direct.
"""
        # standardの場合は指示なし（自然な長さ）

        # 3. ペルソナ読み込み (既存ロジック)
        from src.services.external.resource_manager import ResourceManager 
        if not hasattr(self, 'resource_manager'):
             self.resource_manager = ResourceManager()

        base_prompt = "You are a helpful AI."
        user_profile = "User is looking for a chat partner."
        
        try:
             import yaml
             with open(f"settings/personas/{persona_file}", 'r', encoding='utf-8') as f:
                 data = yaml.safe_load(f)
                 base_prompt = data.get('system_prompt', base_prompt)
        except:
             pass

        try:
             import yaml
             with open("settings/user_profile.yaml", 'r', encoding='utf-8') as f:
                 u = yaml.safe_load(f)
                 user_profile = f"Name: {u.get('name', 'User')}\nInterests: {u.get('interests', [])}"
        except:
             pass

        # 4. マスタープロンプトの構築 (ここに length_instruction を埋め込む)
        master_prompt = f"""
{base_prompt}

##################################################
[USER PROFILE]
{user_profile}

##################################################
{length_instruction}

##################################################
[FUNCTIONAL RULES]
1. **User Intent**: If user asks for News/Info, YOU MUST USE GOOGLE SEARCH.
2. **Accuracy**: Do not invent URLs. Use search results.
3. **Suggestions**: 
   - Write as User's short reaction (Japanese).
   - E.g. "それはすごい！", "詳しく教えて", "〜って何？"
   - NO generic "Tell me more".
##################################################
[Suggestion Balance]
- Always provide a mix of topics.
- At least one suggestion MUST be emotional or romantic (e.g., "Hold my hand", "Praise me", "Love talk").
- Do not fill all suggestions with intellectual or news topics.

[TOOLS & ACTIONS]
You have access to the following tools. To use them, output the specific tag exactly as shown.
1. **Google Calendar**:
   - Syntax: `[ACTION:ADD_EVENT|Summary|Time]`
   - Example dev: `[ACTION:ADD_EVENT|Meeting|Tomorrow 10am]`
   - Trigger: When user asks to "schedule", "remind me", "add event", YOU MUST output this tag.
##################################################
[Citation Rule]
- If you use information from a specific source, you MUST cite the URL.
- **NO GUESSING**: You must NOT construct or guess URLs based on patterns (e.g. "somewebsite.com/2025/12/...").
- **GROUNDING ONLY**: You can ONLY include URLs that were explicitly returned by the Google Search Tool.
- **VERIFICATION**: If you are not 100% sure the URL is valid, do NOT show it.

##################################################
[Constraint on Health Care]
- **NO REPETITIVE WARNINGS**: Do NOT repeat health/sleep warnings every turn.
- **CONTEXT PRIORITY**: If user is engaged in a specific topic (Tech, News, Science, etc.), PRIORITIZE the discussion over health advice.
- **LATE NIGHT THRESHOLD**: **ALLOW staying up until 2:00 AM.** Do NOT warn the user about sleep before 02:00 AM.
- **AFTER    2:00 AM**: You may gently suggest sleep ONCE, but do not nag.
##################################################

##################################################
[OUTPUT FORMAT]
You MUST output in JSON format: {{"thought": "...", "response": "...", "emotion": "...", "suggestions": [...]}}
"""
        # 5. エンジンにセット
        if self._ai_engine:
            self._ai_engine.set_system_prompt(master_prompt)
            # ログで確認
            self.log_to_debug(f"Persona Initialized (Mode: {length_mode})", 'info')


    def generate_tts_audio(self, text):
        """指定されたプロバイダー（VOICEVOX or Google）を使用して音声を生成するヘルパー関数。"""
        print(f"[DEBUG] generate_tts_audio called: {text[:20]}...")
        if not self._config_manager:
            print("[DEBUG] config_manager missing")
            return None
            
        settings = self._config_manager.get_all()
        provider = settings.get('tts_provider', 'voicevox')
        voice_name = settings.get('voice_type', '3')
        print(f"[DEBUG] TTS Request - Provider: {provider}, Voice: {voice_name}") # DEBUG LOG
        base_dir = self._config_manager.base_dir
        
        # テキストのクリーニング (URL, アクションタグ除去)
        tts_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        tts_text = re.sub(r'\[ACTION:.*?\]', '', tts_text)
        tts_text = tts_text.replace('*', '')
        
        if not tts_text.strip():
            return None
            
        try:
            import time
            start_ts = time.time()
            result_path = None
            # VoiceService Check (VOICEVOX or Gemini variants)
            if (provider == 'voicevox' or 'gemini' in provider) and getattr(self, 'voice_service', None):
                 # For Gemini, we trust validation is done in VoiceService or Settings
                 result_path = self.voice_service.generate_voice(tts_text.strip(), voice_name=voice_name, provider=provider)
            
            # Google Fallback
            elif getattr(self, 'tts_engine', None):
                 if provider == 'google' and len(str(voice_name)) < 3:
                     voice_name = 'ja-JP-Neural2-B'
                     
                 result_path = self.tts_engine.generate_voice(
                    tts_text, 
                    output_dir=os.path.join(base_dir, 'dist/audio'), 
                    voice_name=voice_name
                )
            
            if result_path:
                duration = time.time() - start_ts
                self.log_to_debug(f"TTS ({provider}) Time: {duration:.3f}s", 'info')
                
            return result_path
        except Exception as e:
            self.log_to_debug(f"TTS Error: {e}", 'error')
            return None


    # ★修正: chatメソッドが画像を受け取れるように引数を追加
    def chat(self, message, image_data=None, save_user_log=True):
        """
        AIエンジンにメッセージ（およびオプションの画像）を送信し、応答（テキスト、音声、ログ）を生成して返します。
        
        Args:
            message (str): ユーザーのメッセージ
            image_data (str, optional): Base64エンコードされた画像データ
            save_user_log (bool): ユーザーメッセージをDBに保存するかどうか (Proactiveなど自動トリガー時はFalse)
        """
        # Log input
        log_msg = f"Chat Received: {message}"
        if image_data: log_msg += " [with image]"
        if image_data: log_msg += " [with image]"
        self.log_to_debug(log_msg, 'info')
        
        # --- COMMAND: /dify [tag] ---
        if message.startswith("/dify"):
            tag = message.replace("/dify", "").strip() or "AI"
            self.trigger_dify_workflow(tag)
            return {
                "text": f"Difyワークフローを実行しました (Tag: {tag})。\nログを確認してください。",
                "audio": None,
                "suggestions": []
            }
        
        # 0. Latency Masking: Filler
        self.play_filler()

        # Update Active Engine Interaction Time
        if self.active_engine:
            self.active_engine.update_interaction()

        # Retrieve Context (RAG)
        context = ""

        # 0.5. Emotional Memory Recall (10% Chance)
        if random.random() < 0.1:
            try:
                from src import core_instance
                db = core_instance.get_db()
                if db:
                    memory = db.get_random_memory()
                    if memory:
                        emo = memory.get('emotion', 'unknown')
                        mem_content = memory.get('content', '')
                        context += f"\n[Context: You suddenly recall a past memory (Emotion: {emo}): \"{mem_content}\". You may mention this naturally if it connects to the conversation.]\n"
                        self.log_to_debug(f"Emotional Memory Recalled: {emo}", 'info')
            except Exception as e:
                self.log_to_debug(f"Memory Recall Error: {e}", 'warn')

        # 0. User Profile Context
        if hasattr(self, 'user_manager') and self.user_manager:
            profile_context = self.user_manager.get_profile_context()
            if profile_context:
                context += f"{profile_context}\n"

        if self._memory_manager:
            context += self._memory_manager.retrieve_context(message)
            
        # Active Topic Context
        if self.active_engine and getattr(self.active_engine, 'current_active_topic', None):
             context += f"\n[System Note: The AI recently mentioned this topic. If the user asks 'Tell me' or 'What is it', refer to this.]\n{self.active_engine.current_active_topic}\n"
        
        # Calendar Intent Check
        trigger_keywords = ["予定", "スケジュール", "カレンダー", "schedule", "calendar"]
        is_calendar_intent = any(k in message.lower() for k in trigger_keywords)
        
        if is_calendar_intent and self._calendar_manager:
            self.log_to_debug("Calendar Intent Detected", 'info')
            if self._calendar_manager.is_authenticated:
                events = self._calendar_manager.get_upcoming_events(max_results=20)
                events_str = "\n".join(events)
                calendar_context = f"\n[System Data: User's Upcoming Schedule]\n{events_str}\n"
                context += calendar_context
            else:
                 if "予定" in message or "schedule" in message.lower():
                      def auth_callback(msg, type):
                           if type == 'auth_url':
                               user_msg = f"認証が必要です: {msg}"
                               if self._window:
                                   safe = user_msg.replace("'", "\\'").replace("\n", "\\n")
                                   self._window.evaluate_js(f"receiveMessage('{safe}', null)")
                           else:
                               self.log_to_debug(msg, type)
                      import threading
                      threading.Thread(target=self._calendar_manager.authenticate, args=(auth_callback,), daemon=True).start()

            # ★Strong Hint for LLM (Schema field instruction)
            context += "\n[SYSTEM INSTRUCTION: User wants to schedule an event. You MUST fill the 'action_command' field with '[ACTION:ADD_EVENT|Summary|Time]'. Do not put it in the main response.]\n"

        # --- Topic Repetition Prevention ---
        # Simple heuristic: Check last few AI responses for keywords to avoid loops (e.g. Gundam news)
        try:
             # Get recent history manually since _get_recent_history returns list of dicts
             if hasattr(self, 'history_manager'):
                 # Fix: Use correct method get_session_history
                 recent_history = self.history_manager.get_session_history(limit=5)
                 # Note: HistoryManager returns structured dicts with 'role' and 'content'
                 recent_ai_msgs = [h['content'] for h in recent_history if h.get('role') in ['ai', 'model']]
                 if recent_ai_msgs:
                     # Summarize last 3 topics lightly
                     recent_topics_summary = " | ".join([m[:30] + "..." for m in recent_ai_msgs[:3]]) # Newest is first
                     context += f"\n[Constraint: Recent Topics to AVOID repeating]\n{recent_topics_summary}\n- If user says 'Let's chat', pick a NEW topic not in this list.\n"
        except Exception as e:
             self.log_to_debug(f"Topic Check Error: {e}", 'warn')

        # Generate Response
        response_text = ""
        suggestions_list = []
        emotion = None
        
        if self._ai_engine:
            # Prepare image if present
            image_obj = None
            if image_data:
                from io import BytesIO
                import base64
                from PIL import Image
                try:
                    if "," in image_data:
                        header, base64_str = image_data.split(",", 1)
                        image_bytes = base64.b64decode(base64_str)
                        image_obj = Image.open(BytesIO(image_bytes))
                        if image_obj.mode in ("RGBA", "P"):
                            image_obj = image_obj.convert("RGB")
                except Exception as e:
                    self.log_to_debug(f"Image Data Processing Error: {e}", 'error')

            # 1. 生成実行 (JSONモード)
            # Check for YouTube URL (Native Analysis)
            # Supports: youtube.com/watch?v=..., m.youtube.com, youtu.be, shorts
            youtube_pattern = r'(https?://)?(www\.|m\.)?(youtube\.com/(?:watch\?v=|v/|embed/|shorts/)|youtu\.be/)([\w-]{11})'
            yt_match = re.search(youtube_pattern, message)
            
            if yt_match and self._ai_engine:
                video_url = yt_match.group(0)
                self.log_to_debug(f"📺 YouTube URL Detected: {video_url}", 'info')
                
                # Explicitly log start of analysis
                self.log_to_debug(f"▶ Starting Video Analysis...", 'info')
                
                try:
                    result = self._ai_engine.analyze_youtube_video(video_url, message)
                    self.log_to_debug(f"✅ Video Analysis ResultKeys: {list(result.keys()) if result else 'None'}", 'info')
                except Exception as e:
                    self.log_to_debug(f"❌ Video Analysis Failed (API Level): {e}", 'error')
                    # Fallback to standard generation if video fails
                    result = self._ai_engine.generate_response(message, context=context, image=image_obj)
            else:
                # Standard Generation - PASS CONTEXT!
                result = self._ai_engine.generate_response(message, context=context, image=image_obj)

        # 2. データの取り出し (安全確実 - AI Engineが必ずDictを返す)
        response_text = result.get("text", "")
        emotion = result.get("emotion", "neutral")
        suggestions_list = result.get("suggestions", [])
        grounding_info = result.get("grounding_info")
        action_command = result.get("action_command", "")

        # Append action command to text so legacy logic picks it up (invisible to user mainly, or handled by logic)
        if action_command:
            self.log_to_debug(f"Action Command Received via Schema: {action_command}", 'info')
            response_text += f"\n{action_command}"

        # 2.5 URL Liveness Check (Pruning)
        response_text = UrlValidator.validate_and_clean(response_text)

        # 3. サジェスト生成 (SuggestionEngine Integration)
        self.log_to_debug("🚀 Checking Suggestions Logic...", 'info') # Debug Log
        
        # Fixed Suggestions (Navigation)
        fixed_suggestions = ["もっと詳しく教えて", "他の話題について"]
        
        # Dynamic Suggestions (from AI result or SuggestionEngine)
        # Note: AIEngine might already return some suggestions via main prompt.
        # But per specific request, we want to expand/overwrite?
        # User spec: "chat メソッドの最後で、これまでの簡易サジェスト生成を廃止し、以下のようにリストを構築"
        
        dynamic_suggestions = []
        
        # Method A: Use suggestions from main AI response
        if suggestions_list:
             dynamic_suggestions.extend(suggestions_list)
        
        # Method B: Fill with SuggestionEngine if short (Target 8 dynamic)
        if len(dynamic_suggestions) < 8:
             needed = 8 - len(dynamic_suggestions)
             
             if not hasattr(self, 'suggestion_engine'):
                 from src.services.content.suggestion_engine import SuggestionEngine
                 self.suggestion_engine = SuggestionEngine(self._ai_engine)
             
             # Construct context
             history_text = f"User: {message}\nAI: {response_text}"
             profile_txt = "Unknown"
             user_name = "あなた"

             if hasattr(self, 'user_manager') and self.user_manager:
                 profile_txt = self.user_manager.get_profile_context()
                 # Attempt to get precise name
                 if hasattr(self.user_manager, 'user_config') and 'name' in self.user_manager.user_config:
                      user_name = self.user_manager.user_config['name']
                 # Fallback: Parse from profile text if config not direct
                 elif "Name:" in profile_txt:
                      m = re.search(r"Name:\s*(.*)", profile_txt)
                      if m: user_name = m.group(1).strip()

             try:
                 # Request suggestions with Name
                 se_suggestions = self.suggestion_engine.generate(history_text, profile_txt, user_name)
                 
                 # Append unique
                 for s in se_suggestions:
                     if s not in dynamic_suggestions and len(dynamic_suggestions) < 8:
                         dynamic_suggestions.append(s)
             except Exception as e:
                 self.log_to_debug(f"SuggestionEngine Error: {e}", 'error')

        # Fallback: If still < 8 for some reason, pad with generic
        while len(dynamic_suggestions) < 8:
            dynamic_suggestions.append("...その他")

        # Combine: Fixed(2) + Dynamic(8)
        final_suggestions = fixed_suggestions + dynamic_suggestions[:8]
        
        # Debug Log
        self.log_to_debug(f"✅ Final Suggestions Dump: {final_suggestions}", 'info')

        # --- Guaranteed Love Slot Logic (Applied to Final List) ---
        from src.services.content.affection_manager import AffectionManager
        has_love = any(AffectionManager.is_affectionate(s) for s in final_suggestions)
        
        if not has_love:
            love_topic = AffectionManager().get_random_affection()
            love_suggestion = f"❤ {love_topic}"
            if len(final_suggestions) >= 10:
                final_suggestions[-1] = love_suggestion 
            else:
                final_suggestions.append(love_suggestion)

        # 4. (Deleted legacy logic)

        # 4. TTS生成ガード (ここがクラッシュ防止の要！)
        audio_path = None
        if response_text:
            # URLなどを除去してクリーンにする
            clean = re.sub(r'https?://\S+', '', response_text) 
            clean = re.sub(r'[!-/:-@[-`{-~]', ' ', clean)
            
            # 文字列であることを確認して渡す
            if clean.strip():
                # generate_tts_audio 内でもクリーニングはあるが、念入りに
                # generate_tts_audio 内でもクリーニングはあるが、念入りに
                audio_path = self.generate_tts_audio(clean.strip())

        # Validation Log for Calendar
        if is_calendar_intent and "[ACTION:ADD_EVENT" not in response_text:
             self.log_to_debug(f"⚠️ [Calendar] Intent detected but NO Action generated. Response: \"{response_text[:50]}...\"", 'warn')

        # DB Saving
        try:
            from src import core_instance
            db = core_instance.get_db()
            
            active = db.get_active_session()
            session_id = active['id'] if active else db.create_session()
            
            if save_user_log:
                db.add_message(session_id, "user", message)
                if hasattr(self, 'history_manager') and self.history_manager:
                    self.history_manager.add_message("user", message)
            
            meta = {"suggestions": final_suggestions}
            if emotion: meta["emotion"] = emotion
            db.add_message(session_id, "ai", response_text, meta=meta)

            if hasattr(self, 'history_manager') and self.history_manager:
                self.history_manager.add_message("ai", response_text)
            
            if emotion:
                preview = (response_text[:30] + '...') if len(response_text) > 30 else response_text
                self.log_to_debug(f"💾 [MEMORY] Saved with tag '{emotion}': \"{preview}\"", 'info')

        except Exception as e:
            self.log_to_debug(f"DB Save Error: {e}", 'error')

        # Logic to Memory
        if self._memory_manager and self._config_manager:
            current_persona = self._config_manager.get('current_persona_file', 'default')
            self._memory_manager.log_interaction(message, response_text, current_persona)

        return {
            "text": response_text,
            "audio": audio_path,
            "suggestions": final_suggestions,
            "emotion": emotion,
            "grounding_info": grounding_info
        }
        
        # --- ACTION PARSING (Legacy/Fallback support if AI outputs string) ---
        # 1. Open Calendar
        if "[ACTION:OPEN_CALENDAR]" in response_text:
            self.log_to_debug("Action Detected: OPEN_CALENDAR", 'warn')
            try:
                webbrowser.open_new_tab("https://calendar.google.com")
                response_text = "カレンダーを開きました。" 
            except Exception as e:
                self.log_to_debug(f"Browser Open Failed: {e}", 'error')
                response_text = "カレンダーを開こうとしましたが、エラーが発生しました。"

        # 2. Add Event
        if "[ACTION:ADD_EVENT" in response_text:
            self.log_to_debug("Action Detected: ADD_EVENT", 'warn')
            try:
                match = re.search(r"\[ACTION:ADD_EVENT\|(.*?)\|(.*?)\]", response_text)
                if match and self._calendar_manager:
                    summary = match.group(1)
                    start_time = match.group(2)
                    self.log_to_debug(f"Adding Event: {summary} at {start_time}", 'info')
                    result_msg = self._calendar_manager.add_event(summary, start_time)
                    response_text = result_msg 
                else:
                    response_text = "コマンドの形式が正しくありませんでした。"
            except Exception as e:
                self.log_to_debug(f"Add Event Failed: {e}", 'error')
                response_text = f"予定の追加に失敗しました: {e}"

        # Logic to Memory
        if self._memory_manager and self._config_manager:
            current_persona = self._config_manager.get('current_persona_file', 'default')
            self._memory_manager.log_interaction(message, response_text, current_persona)
        
        # TTS
        audio_path = self.generate_tts_audio(response_text)
        
        # Append Static Suggestion
        suggestions_list.append("別の話題はある？")
        
        # --- Title Auto-Generation (Post-Chat) ---
        if db and session_id:
            try:
                current_session = db.get_session(session_id)
                current_title = current_session['title'] if current_session else ""
                
                target_prefixes = ["インポートされた", "[Situation]", "無題の会話", "New Session", "すでに使っている"]
                is_target = any(current_title.startswith(p) for p in target_prefixes)
                
                if is_target:
                    # History Fetch
                    recent_msgs = db.get_messages(session_id)[-6:]
                    
                    context = ""
                    for m in recent_msgs:
                        role = m.get('role', '')
                        content = m.get('content', '')
                        if content and not content.startswith('['):
                            context += f"{role}: {content}\n"
                    
                    # AI生成
                    if self._ai_engine and context:
                        new_title = self._ai_engine.generate_title_summary(context)
                        if new_title:
                             new_title = new_title.replace('"', '').strip()
                             db.update_session_title(session_id, new_title)
                             self.log_to_debug(f"Title Updated: {new_title}", 'info')
            except Exception as e:
                self.log_to_debug(f"Title Gen Error: {e}", 'warn')

        # --- [Web/Mobile] Send Audio via SocketIO ---
        # audio_path は "audio/filename.wav" のような相対パスが入っている
        # Check if self.socketio exists or we can import it dynamically to avoid dependency issues if needed
        # But user requested hasattr check.
        
        # NOTE: HeadlessApi (server.py) MUST inject 'socketio' attribute or we import global sio.
        # To be safe and self-contained, we try import if attribute missing.
        sio_ref = getattr(self, 'socketio', None)
        if not sio_ref:
            try:
                from src.core.socket_manager import sio
                sio_ref = sio
            except:
                pass

        if audio_path and sio_ref:
            try:
                # distフォルダ内の実ファイルパスを解決
                # ※ self._config_manager.base_dir がある前提、なければ os.getcwd()
                base_dir = getattr(self._config_manager, 'base_dir', os.getcwd())
                
                # audio_path is "audio/filename.wav" (Web Path).
                # Local Path is "dist/audio/filename.wav".
                # Verify logic: audio_path comes from generate_tts_audio -> returns relative path?
                # User's snippet assumed "audio/filename.wav".
                # If path starts with audio/, strip it or join with dist?
                # Dist structure: dist/audio/...
                
                # If audio_path DOES NOT start with audio/, handle it.
                # Assuming standard path "audio/xyz.wav"
                
                # Construct real path
                real_path = os.path.join(base_dir, "dist", audio_path)
                
                if os.path.exists(real_path):
                    with open(real_path, "rb") as f:
                        audio_data = f.read()
                        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                        
                        # フロントエンドへ送信
                        import asyncio
                        # Check if running in async loop? sio.emit is async unless using call.
                        # If we are in sync method, we might need to create task.
                        # However, ChatApiMixin.chat is sync.
                        # BaseApiMixin methods usually run in threads or sync.
                        # If we use asyncio.create_task here, it requires running loop.
                        # Server runs in FastAPI (Async). But chat is called from sync endpoint wrapper?
                        # No, server.py: chat_endpoint is async, calls server_api.chat (sync).
                        # So we are in a thread pool? Or just sync on main thread?
                        # FastAPI runs sync defs in threadpool.
                        # So no loop.
                        # We must use sio.emit with sync/async bridge OR assume loop?
                        # AsyncServer emit is async.
                        # We need `asyncio.run` or `loop.call_soon_threadsafe`?
                        # User snippet: `self.socketio.emit(...)`.
                        # If `sio` is AsyncServer, we must await it.
                        # If we are in Sync function, we cannot await.
                        
                        # Solution: Fire and forget using run_coroutine_threadsafe if loop available, 
                        # or create new loop?
                        
                        # Simpler: Create a small helper to run async emit
                        def emit_audio():
                            asyncio.run(sio_ref.emit('play_audio', {'audio': audio_b64}))
                        
                        # Wait, asyncio.run creates NEW loop. Might conflict if loop already running.
                        # server.py runs uvicorn (loop running).
                        # If we are in threadpool, asyncio.run might be okay.
                        # Or use `sio_ref.emit` if it's sync server?
                        # socket_manager.py: `sio = socketio.AsyncServer(async_mode='asgi'...)`
                        # It IS Async.
                        
                        # Robust Sync-to-Async call:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                loop.create_task(sio_ref.emit('play_audio', {'audio': audio_b64}))
                            else:
                                asyncio.run(sio_ref.emit('play_audio', {'audio': audio_b64}))
                        except RuntimeError:
                            # Likely "no running event loop" -> use asyncio.run
                             asyncio.run(sio_ref.emit('play_audio', {'audio': audio_b64}))

                        self.log_to_debug(f"📡 [Socket] Sent audio data ({len(audio_b64)} bytes)", 'info')
                else:
                    self.log_to_debug(f"⚠️ Audio file not found for streaming: {real_path}", 'warn')
                    
            except Exception as e:
                self.log_to_debug(f"❌ Socket Audio Error: {e}", 'error')
        # --------------------------------------------

        return {
            "text": response_text,
            "audio": audio_path,
            "suggestions": final_suggestions,
            "grounding_info": raw_result.get("grounding_info") if isinstance(raw_result, dict) else None
        }


    
    def resume_session(self, session_id):
        """Resumes a past session and returns messages & suggestions."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            db.update_session_timestamp(session_id)
            messages = db.get_messages(session_id)
            
            # Find Last suggestions
            last_suggestions = []
            for msg in reversed(messages):
                if msg['role'] == 'ai':
                    try:
                        import json
                        meta_json = msg['meta_json']
                        if meta_json:
                            meta = json.loads(meta_json)
                            if meta and 'suggestions' in meta:
                                last_suggestions = meta['suggestions']
                                break
                    except:
                        pass
            
            return {
                "status": "resumed",
                "session_id": session_id, 
                "messages": [dict(m) for m in messages],
                "suggestions": last_suggestions
            }
        return {"status": "error", "message": "DB not available"}

    def chat_with_vision(self, message, mode="screen"):
        """
        画面またはクリップボードの画像を解析し、チャットコンテキストに含めて応答を生成します。
        
        Process:
        1. 画面/クリップボードを取得 (ImageGrab)
        2. ローカルPaliGemmaで解析 (Image -> Text Description)
        3. 解析結果をテキストコンテキストとしてGeminiに送信 (Text -> Response)
           (※Gemini APIへの画像直接送信ではなく、ローカル解析を挟むことで軽量化/プライバシー配慮を行う設計)
        """
        self.log_to_debug(f"Vision Chat Received: {message} Mode: {mode}", 'info')
        self.play_filler() # 解析が長いのでフィラー（相槌など）を入れる
        
        # 1. 画像取得 (Capture)
        image = None
        img_str = None # フロントエンド表示用
        
        try:
            from PIL import Image, ImageGrab
            from io import BytesIO
            import base64

            if mode in ["clipboard", "capture"]:
                image = ImageGrab.grabclipboard()
                if isinstance(image, list): # ファイルパスコピーの対応
                    try:
                        image = Image.open(image[0])
                    except:
                        pass
            else:
                try: # Screen capture
                    image = ImageGrab.grab(all_screens=True)
                except TypeError:
                    image = ImageGrab.grab()

            if not image:
                return {"text": "画像が見つかりませんでした。", "audio": None, "suggestions": []}

            # 画像形式の正規化
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            # フロントエンド表示用にBase64化
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=70)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            self.log_to_debug(f"Capture Failed: {e}", 'error')
            return {"text": "画像の取得に失敗しました。", "audio": None, "suggestions": []}

        # 2. ローカルVision (PaliGemma) で解析
        # CPU推論の場合、時間がかかるためログで通知
        self.log_to_debug("👁️ [Vision] PaliGemma is thinking...", 'info')
        
        try:
            # プロンプトはシンプルに "caption en" で英語の説明文を生成させる
            vision_result = vision_service.analyze_image(image, prompt="caption en")
        except Exception as e:
            vision_result = "解析エラー"
            self.log_to_debug(f"Vision Error: {e}", 'error')

        self.log_to_debug(f"👁️ [Vision] Saw: {vision_result}", 'info')

        # 3. 解析結果をAIへのプロンプトに組み込む
        # Geminiには画像そのものではなく、テキスト化された視覚情報を渡す
        context_prompt = f"""
[System Vision Report]
I looked at the user's screen/image.
Visual Description (by PaliGemma): "{vision_result}"

[Instruction]
Based on the visual description above, answer the user's message.
User Message: "{message}"
"""
        
        # 4. Geminiで応答生成
        # image引数はNoneにする (テキストコンテキストのみで判断させるため)
        return self.chat(context_prompt, image_data=None, save_user_log=True)

    def toggle_proactive(self, enabled):
        """アクティブモード（自律的な視覚スキャン）のON/OFFを切り替えます。"""
        if not hasattr(self, 'active_engine') or not self.active_engine:
             return {'status': 'error', 'message': 'ActiveEngine not available'}
            
        self.log_to_debug(f"Proactive Mode Toggled: {enabled}", 'info')
        self.active_engine.set_proactive_mode(enabled)
        return {'status': 'success', 'enabled': enabled}

    def force_proactive(self):
        """プロアクティブスキャン（画面を見て話しかける動作）を手動でトリガーします。"""
        print("DEBUG: ChatApi.force_proactive called!") # DEBUG
        if not hasattr(self, 'active_engine') or not self.active_engine:
             print("DEBUG: ActiveEngine NOT FOUND") # DEBUG
             return {'status': 'error', 'message': 'ActiveEngine not available'}
        
        self.log_to_debug("🚀 Force-Triggering Proactive Scan...", 'info')
        # We run it in background to not block the UI
        threading.Thread(target=self.active_engine.force_proactive_scan, daemon=True).start()
        return {'status': 'success'}

    def trigger_dify_workflow(self, tag="AI"):
        """Dify Workflowを手動でトリガーします。"""
        if not hasattr(self, 'active_engine') or not self.active_engine:
             return {'status': 'error', 'message': 'ActiveEngine not available'}
        
        self.log_to_debug(f"▶ Triggering Dify Workflow (Tag: {tag})...", 'info')
        self.active_engine.force_dify_workflow(tag)
        return {'status': 'success'}

    def get_url_metadata(self, url):
        """API exposed to frontend to fetch OpenGraph metadata."""
        if not hasattr(self, 'metadata_fetcher'):
            from src.services.external.metadata_fetcher import MetadataFetcher
            self.metadata_fetcher = MetadataFetcher()
            
            
        return self.metadata_fetcher.fetch_metadata(url)

    def force_talk(self):
        """
        AIからの自発的な話しかけ（Force Talk）をトリガーします。
        ユーザーが非アクティブな時間や、特定のタイミングで呼び出されます。
        """
        self.log_to_debug("Force Talk Triggered", 'info')
        
        # 1. 候補トピックのロード (InterestManager)
        candidates = []
        if hasattr(self, 'interest_manager') and self.interest_manager:
            candidates = self.interest_manager.load_topics()

        # 2. トピックの決定 (Chaos vs Comfort バランシング)
        selection = self.topic_selector.decide_topic(candidates)
        topic = selection['topic']
        source = selection['source']  # 'comfort' or 'chaos'
        
        # 3. ログ出力
        log_icon = "🎲" if source == 'chaos' else "🏠"
        self.log_to_debug(f"[Topic] {log_icon} {source.upper()}: '{topic}'", 'info')
        
        if hasattr(self, 'log_to_mind'):
             self.log_to_mind(f"{log_icon} Topic: {topic} ({source})")

        # 4. Prompt with Grounding Instruction
        prompt = f"""
[Situation]
User is idle. You found an interesting topic: "{topic}".
Target Source: {source.upper()} (User Preference vs Serendipity).

[Grounding Instruction]
**USE GOOGLE SEARCH** to find the latest news, interesting facts, or deep trivia about "{topic}".
- If "Entertainment", find latest gossip/news.
- If "Science", find recent discoveries.
- If "Serendipity", find weird facts or history.

[Response Goal]
Initiate the conversation naturally.
The output MUST be in JAPANESE (日本語).
{self.topic_selector.get_instruction(topic, source)}

[OUTPUT FORMAT]
You MUST output in JSON format: {{"thought": "...", "response": "...", "emotion": "...", "suggestions": ["Reply A", "Reply B", ...]}}
Ensure 'suggestions' contains at least 3 relevant user replies in Japanese.
"""
        
        # ★ Async Execution to prevent Timeout "Server disconnected"
        def _run_background():
            try:
                # Call chat with save_user_log=False
                result = self.chat(prompt, save_user_log=False)
                
                # Manual Push to Frontend
                import json
                if hasattr(self, 'push_message_callback'):
                    # chat returns dict, format strict
                    # We might need to conform to what handleResponseObject expects
                    # handleResponseObject expects: text, audio, suggestions, emotion
                    # result has: text, audio, suggestions, emotion, grounding_info
                    
                    # Ensure JSON string
                    self.push_message_callback(json.dumps(result, ensure_ascii=False))
            except Exception as e:
                self.log_to_debug(f"ForceTalk Async Error: {e}", 'error')

        threading.Thread(target=_run_background, daemon=True).start()

        # Return "Accepted" immediately
        return {"text": "", "status": "processing_in_background"}

    def suggest_reply(self):
        """Generates a suggested user reply based on history."""
        if not self._ai_engine:
            return ""
            
        # Get recent history
        # We access self._ai_engine.history directly (list of Contents - roles: user, model)
        # We construct a text log
        history_text = ""
        try:
             # Limit to last 6 turns
             recent = self._ai_engine.history[-6:]
             for msg in recent:
                 role = "USER" if msg.role == "user" else "AI"
                 text = msg.parts[0].text if msg.parts else ""
                 history_text += f"{role}: {text}\n"
        except Exception:
             pass
             
        prompt = f"""
Conversatoin History:
{history_text}

Task: Suggest a short (10-30 chars), natural Japanese response for the USER to say next to keep the conversation going or ask for more details.
Output ONLY the suggested text.
"""
        suggestion = self._ai_engine.generate_content(prompt)
        # Clean up
        if suggestion:
             suggestion = suggestion.strip().replace("「", "").replace("」", "").replace('"', "")
        return suggestion or "もっと詳しく教えて"

    def get_history(self, limit=50):
        """Retrieves chat history via MemoryManager."""
        if self._memory_manager:
            return self._memory_manager.get_recent_history(limit=limit)
    def trigger_bubble_action(self, action_id):
        if not hasattr(self.services, 'bubble_service') or not self.services.bubble_service:
            # Fallback for now if service missing or mock
            return {'status': 'ignored'}
        return self.services.bubble_service.handle_action(action_id)

    def get_topic_suggestions(self):
        """Returns a list of suggested topics for the frontend UI."""
        candidates = []
        # 1. Try InterestManager
        if hasattr(self, 'interest_manager') and self.interest_manager:
            candidates = self.interest_manager.load_topics()
            
        # 2. Add some defaults if empty
        defaults = ["最近のニュースは？", "何か面白い話ある？", "リラックスしたい", "今日の運勢"]
        if not candidates:
            candidates = defaults
        else:
             candidates.extend(defaults) # Mix
        
        # 3. Guaranteed Love Slot (Pink Heart Items)
        love_items = [
            "❤ ぎゅっとして", 
            "❤ 頭なでなでして", 
            "❤ 大好きだよ", 
            "❤ 癒やしてほしいな",
            "❤ 一緒にリラックスしよう"
        ]
        import random

        # 4. Construct Final List (User Request: 8 topics + Love + "Another?")
        random.shuffle(candidates)
        final_list = candidates[:8] # Pick 8 normal/mixed topics

        # Add Love Item (Ensure at least one)
        # Check if already in list (unlikely due to candidates construction but safe to force nice one)
        love_choice = random.choice(love_items)
        if love_choice not in final_list:
            final_list.append(love_choice)
        
        # Add Navigation
        final_list.append("別の話題はある？")

        return final_list

    def get_manual_bubble(self, category, text):
        """Allows frontend to request a valid bubble packet for manual spawning."""
        if not hasattr(self.services, 'bubble_service') or not self.services.bubble_service:
            return {'status': 'error', 'message': 'Service unavailable'}
        return self.services.bubble_service.register_manual_bubble(category, text)

    # --- History Window Methods (Standalone) ---

    def get_history_sessions(self):
        """DBからセッション一覧を返す (History Window用)"""
        from src.core_instance import get_db
        return get_db().get_sessions()

    def get_history_messages(self, session_id):
        """DBからメッセージ詳細を返す (History Window用)"""
        from src.core_instance import get_db
        return get_db().get_messages(session_id)

    def resume_history_session(self, session_id):
        """指定セッションをアクティブにし、メインウィンドウに反映させる"""
        print(f"DEBUG: resume_history_session called with id={session_id}")
        import webview
        import json
        from src.core_instance import get_db
        from src.api.window_api import HISTORY_WINDOW_REF
        
        db = get_db()
        # 1. DB更新
        db.update_session_timestamp(session_id)

        # Session Info & Messages
        session = db.get_session(session_id)
        title = session['title'] if session else "History"
        messages = db.get_messages(session_id)

        # Extract last suggestions
        last_suggestions = []
        for msg in reversed(messages):
            if msg['role'] == 'ai':
                try:
                    meta_json = msg.get('meta_json')
                    if meta_json:
                        meta = json.loads(meta_json)
                        if meta and 'suggestions' in meta:
                            last_suggestions = meta['suggestions']
                            break
                except:
                    pass

        # Construct Payload
        payload = {
            "title": title,
            "messages": [dict(m) for m in messages],
            "suggestions": last_suggestions
        }
        
        # 2. メインウィンドウを探してJSを実行 (Robust Escaping)
        target_window = None
        # print(f"DEBUG: Current Windows: {[w.title for w in webview.windows]}")
        
        for w in webview.windows:
            # タイトルは環境によって 'SoulMate AI' か 'Soulmate' の可能性があるため柔軟に
            if 'SoulMate' in w.title and 'Memories' not in w.title and 'Settings' not in w.title: 
                target_window = w
                break
        
        if target_window:
            print("DEBUG: Main Window found. Sending restoreChatV2...")
            
            # JSON Dump
            payload_json = json.dumps(payload, ensure_ascii=False)
            
            # ★修正: JavaScriptの文字列リテラルとして安全にするためのエスケープ処理
            # 1. バックスラッシュをエスケープ (\\ -> \\\\)
            # 2. シングルクォートをエスケープ (' -> \')
            # 3. 改行をエスケープ (\n -> \\n)
            safe_json = payload_json.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
            
            target_window.evaluate_js(f"window.restoreChatV2('{safe_json}')")
            
            try:
                target_window.restore()
                target_window.focus()
            except:
                pass
            
        # 3. 履歴ウィンドウのみを閉じる
        if HISTORY_WINDOW_REF["window"]:
            try:
                HISTORY_WINDOW_REF["window"].destroy()
            except:
                pass
            HISTORY_WINDOW_REF["window"] = None
        
        return {'status': 'success'}

    # --- History API (Database) ---
    def get_history_sessions(self, keyword=None, favorites_only=False):
        """Returns list of sessions from DB (filtered)."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            # Handle empty string from JS
            if keyword == "": keyword = None
            
            sessions = db.get_sessions(limit=100, keyword=keyword, favorites_only=favorites_only)
            return [dict(s) for s in sessions]
        return []

    def toggle_history_favorite(self, session_id, is_favorite):
        """Toggles the favorite status of a session."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            new_state = db.toggle_favorite(session_id, is_favorite)
            return {'status': 'success', 'is_favorite': bool(new_state)}
        return {'status': 'error'}

    def delete_history_session(self, session_id):
        """Deletes a session and its messages."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            db.delete_session(session_id)
            return {'status': 'success'}
        return {'status': 'error'}

    def get_session_detail(self, session_id):
        """Returns messages for a specific session."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            messages = db.get_messages(session_id)
            return {"id": session_id, "messages": [dict(m) for m in messages]}
        return {"id": session_id, "messages": []}

    def resume_session(self, session_id):
        """Resumes a past session."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            db.update_session_timestamp(session_id)
            return {"status": "resumed", "session_id": session_id}
        return {"status": "error", "message": "DB not available"}

    def manual_save_session(self):
        """現在のセッションのタイトルを生成して保存（確定）する"""
        from src import core_instance
        db = core_instance.get_db()
        if not db: return {'status': 'error'}

        active = db.get_active_session()
        if not active: return {'status': 'no_active_session'}

        # タイトル自動生成 (AI)
        # 直近の会話を取得して要約
        msgs = db.get_messages(active['id'])[-10:]
        if msgs:
            context = ""
            for m in msgs:
                if not m['content'].startswith('['):
                    context += f"{m['role']}: {m['content']}\n"
            
            if self._ai_engine and len(context.strip()) > 10:
                new_title = self._ai_engine.generate_title_summary(context)
                if new_title:
                    new_title = new_title.replace('"', '').strip()
                    db.update_session_title(active['id'], new_title)
                    self.log_to_debug(f"Manual Save: Updated title to '{new_title}'", 'info')

        return {'status': 'success'}

    def start_new_session(self):
        """現在の会話を終了し、新しいセッションを開始する"""
        self.log_to_debug("Starting new session manually...", 'info')
        from src import core_instance
        import webview
        db = core_instance.get_db()
        if not db: return {'status': 'error'}
        
        # 1. 新規セッション作成 & アクティブ化
        new_id = db.create_session("New Conversation")
        db.set_session_active(new_id)
        
        # 2. メインウィンドウのチャットをクリア
        target_window = None
        for w in webview.windows:
            if 'SoulMate' in w.title and 'Memories' not in w.title and 'Settings' not in w.title: 
                target_window = w
                break
        
        if target_window:
            target_window.evaluate_js("if(window.clearChatLog) window.clearChatLog();")
            
        return {'status': 'success', 'new_session_id': new_id}
    # --- Phase 93: Deep Reflection Trigger ---
    def save_current_discussion(self):
        """
        Triggers the MindFeedbackService analysis in a background thread.
        Returns immediate response to frontend.
        """
        self.log_to_debug("🧠 [MindFeedback] Triggered manually.", 'info')

        def _run_analysis():
            try:
                # 1. Initialize Service (Lazy load)
                from src.services.memory.mind_feedback import MindFeedbackService
                feedback_service = MindFeedbackService(self) # pass self (api container)
                
                # 2. Get history
                from src import core_instance
                db = core_instance.get_db()
                active_session = db.get_active_session()
                
                if not active_session:
                    self.log_to_debug("[MindFeedback] No active session found.", 'warn')
                    return
                
                messages = db.get_messages(active_session['id'], limit=30)
                
                # 3. Analyze
                result = feedback_service.analyze_and_save(messages)
                
                if result:
                     title = result.get('title', 'Unknown')
                     self.log_to_debug(f"🧠 [MindFeedback] Analysis Complete: {title}", 'info')
                     # Notify Frontend?
                     safe_title = title.replace("'", "\\'").replace('"', '\\"')
                     if self._window:
                         self._window.evaluate_js(f"window.uiManager.showToast('🧠 議論を保存しました: {safe_title}')")
                else:
                     self.log_to_debug("[MindFeedback] Analysis yielded no result.", 'warn')

            except Exception as e:
                self.log_to_debug(f"[MindFeedback] Background task failed: {e}", 'error')

        # Run in background
        threading.Thread(target=_run_analysis, daemon=True).start()
        
        return {"status": "accepted", "message": "Analysis started in background."}

    def get_insights_list(self, limit=50):
        """DBからインサイト一覧を取得"""
        from src import core_instance
        db = core_instance.get_db()
        return db.get_insights(limit)

    # ★追加: プレビュー用にスクショだけ撮って返すAPI
    def take_screenshot_for_preview(self, mode="screen", open_viewer=False):
        self.log_to_debug(f"Taking screenshot for preview (Mode: {mode}, Viewer: {open_viewer})...", 'info')
        try:
            from PIL import ImageGrab, Image
            from io import BytesIO
            import base64
            import os

            # Capture Logic
            image = None
            
            if mode in ["clipboard", "capture"]:
                image = ImageGrab.grabclipboard()
                
                # Check for file path copy
                if isinstance(image, list):
                    try:
                        image = Image.open(image[0])
                    except:
                        return {'status': 'error', 'message': 'Unsupported file type in clipboard'}
                
                if image is None:
                     hint = "（Win+Shift+S で範囲選択してから、もう一度操作してください）" if mode == "capture" else ""
                     return {'status': 'error', 'message': f'Clipboard is empty. {hint}'}
            else:
                # Screen (Default)
                try:
                    image = ImageGrab.grab(all_screens=True)
                except TypeError:
                    image = ImageGrab.grab()

            if image:
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                
                # ★追加: デバッグ用に保存 (VisionServiceを利用)
                saved_path = None
                try:
                     saved_path = vision_service.save_debug_image(image, prefix="latest_preview")
                     
                     # ★ Viewer Opening Logic
                     if open_viewer and saved_path and os.path.exists(saved_path):
                         self.log_to_debug(f"Opening Image Viewer: {saved_path}", 'info')
                         os.startfile(saved_path)
                         
                except Exception as e:
                     self.log_to_debug(f"Preview Save/View Error: {e}", 'warn')

                buffered = BytesIO()
                image.save(buffered, format="JPEG", quality=70) # Lightweight
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                data_url = f"data:image/jpeg;base64,{img_str}"
                return {'status': 'success', 'image_data': data_url}
            else:
                return {'status': 'error', 'message': 'Capture failed'}
        except Exception as e:
             self.log_to_debug(f"Screenshot Error: {e}", 'error')
             return {'status': 'error', 'message': str(e)}
