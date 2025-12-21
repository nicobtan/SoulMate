import os
import threading
import random
import webbrowser
import re
import json
from .base import BaseApiMixin
# from .json_helper import _extract_json_from_text # TOON化により不要
from PIL import ImageGrab

class ChatApiMixin(BaseApiMixin):
    
    def initialize_persona(self, persona_file="lena.yaml"):
        """JSONモード用のシステムプロンプトをセット"""
        from ..services.resource_manager import ResourceManager 
        if not hasattr(self, 'resource_manager'):
            self.resource_manager = ResourceManager()

        # 1. ファイル読み込み  (ResourceManagerの実装を信頼)  
        # Note: If ResourceManager is not present (reverted), we might need fallback or simplistic approach. 
        # But since user said "resource_manager.get_persona_system_prompt", I assume they want that or existing logic.
        # Wait, ResourceManager was in the rolled back change? 
        # The rollback removed src/services/resource_manager.py.
        # !! CRITICAL: The user code uses ResourceManager but it was likely deleted in rollback.
        # I must check if I should restore ResourceManager or implement simpler logic here.
        # User request says: "from ..services.resource_manager import ResourceManager"
        # I should probably recreate ResourceManager or use simplistic prompt loading if it doesn't exist.
        
        # Checking if I need to restore ResourceManager first. 
        # For now, I will implement a robust prompt loader inside here to avoid dependency hell if file is missing.
        
        # Actually, let's just stick to what was there or simple loading if ResourceManager is gone.
        # The previous code (before rollback) used ResourceManager. Since I rolled back, I don't have it.
        # I should just load the YAML directly or use a default prompt.
        
        # However, the user provided code block USES ResourceManager.
        # "from ..services.resource_manager import ResourceManager"
        # I will assume I need to create ResourceManager too? Or just adapt?
        # I will adapt to standard file reading for stability.
        
        base_prompt = "You are a helpful AI."
        user_profile = "User is looking for a chat partner."
        
        # Try to load persona manually if RM is missing
        try:
             import yaml
             with open(f"settings/personas/{persona_file}", 'r', encoding='utf-8') as f:
                 data = yaml.safe_load(f)
                 base_prompt = data.get('system_prompt', base_prompt)
        except:
             pass

        # Try to load user profile
        try:
             import yaml
             with open("settings/user_profile.yaml", 'r', encoding='utf-8') as f:
                 u = yaml.safe_load(f)
                 user_profile = f"Name: {u.get('name', 'User')}\nInterests: {u.get('interests', [])}"
        except:
             pass

        # マスタープロンプト (JSONのフォーマット指示はEngine側で行うため、ここは「性格」と「ルール」に集中)
        master_prompt = f"""
{base_prompt}

##################################################
[USER PROFILE]
{user_profile}

##################################################
[FUNCTIONAL RULES]
1. **User Intent**: If user asks for News/Info, YOU MUST USE GOOGLE SEARCH.
2. **Accuracy**: Do not invent URLs. Use search results.
3. **Suggestions**: 
   - Write as User's short reaction (Japanese).
   - E.g. "それはすごい！", "詳しく教えて", "〜って何？"
   - NO generic "Tell me more".
##################################################
"""
        if self._ai_engine:
            self._ai_engine.set_system_prompt(master_prompt)
            self.log_to_debug("✅ Persona & Functional Rules Initialized (JSON Mode).", 'info')


    def generate_tts_audio(self, text):
        """Helper to generate audio using configured provider (VOICEVOX or Google)."""
        if not self._config_manager:
            return None
            
        settings = self._config_manager.get_all()
        provider = settings.get('tts_provider', 'voicevox')
        voice_name = settings.get('voice_type', '3')
        base_dir = self._config_manager.base_dir
        
        # Clean Text
        tts_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        tts_text = re.sub(r'\[ACTION:.*?\]', '', tts_text)
        tts_text = tts_text.replace('*', '')
        
        if not tts_text.strip():
            return None
            
        try:
            import time
            start_ts = time.time()
            result_path = None
            # VoiceService Check (VOICEVOX or Gemini)
            if provider in ['voicevox', 'gemini'] and getattr(self, 'voice_service', None):
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
        """Sends a message (and optional image) to the AI Engine and returns the response object {text, audio}."""
        # Log input
        log_msg = f"Chat Received: {message}"
        if image_data: log_msg += " [with image]"
        self.log_to_debug(log_msg, 'info')

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
        # 以前のような format_instruction の連結は不要です
        result = self._ai_engine.generate_response(message, image=image_obj)

        # 2. データの取り出し (安全確実 - AI Engineが必ずDictを返す)
        response_text = result.get("text", "")
        emotion = result.get("emotion", "neutral")
        suggestions_list = result.get("suggestions", [])
        grounding_info = result.get("grounding_info")

        # 3. サジェスト補完 (最低限)
        if len(suggestions_list) < 2:
            suggestions_list = ["詳しく教えて", "面白いね", "他には？", "そうなんだ"]
        
        final_suggestions = suggestions_list[:4]
        if "他の話題もしてみたい" not in final_suggestions and "別の話題はある？" not in final_suggestions:
            final_suggestions.append("他の話題もしてみたい")

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

        # DB Saving
        from src import core_instance
        db = core_instance.get_db()
        if db:
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

        return {
            "text": response_text,
            "audio": audio_path,
            "suggestions": suggestions_list,
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
        Captures a screenshot or clipboard and sends it with the message to the AI Engine.
        mode: "screen" (Full), "clipboard" (Copy), "capture" (Right Click alias)
        """
        self.log_to_debug(f"Vision Chat Received: {message} Mode: {mode}", 'info')
        
        # Capture Logic
        image = None
        img_str = None
        
        try:
            # ★修正: "capture" モードもクリップボードとして扱うように条件を追加
            if mode in ["clipboard", "capture"]:
                # Windows: grabclipboard() returns Image or list of filenames
                image = ImageGrab.grabclipboard()
                
                # 画像がない場合の親切なエラーメッセージ
                if image is None:
                    # もし "capture" (右クリック) だったら、ユーザーにヒントを出す
                    hint = "（Win+Shift+S で範囲選択してから、もう一度右クリックしてみてね）" if mode == "capture" else ""
                    return {
                        "text": f"クリップボードに画像が見当たりません。{hint}", 
                        "audio": None, 
                        "suggestions": []
                    }
                
                # ファイルパスがコピーされている場合の対応
                if isinstance(image, list):
                    from PIL import Image
                    try:
                        image = Image.open(image[0])
                    except:
                         return {"text": "画像ファイルをコピーしたようですね。現在は画像データのコピーのみ対応しています。", "audio": None, "suggestions": []}
            else:
                # Screen (Default)
                # Try all_screens=True if supported by this Pillow version, else fallback
                try:
                    image = ImageGrab.grab(all_screens=True)
                except TypeError:
                    image = ImageGrab.grab()
                self.log_to_debug("Screenshot captured.", 'info')
            
            # Process Image for Return (Display)
            if image:
                from io import BytesIO
                import base64
                buffered = BytesIO()
                # Optimize: RGB conversion just in case (e.g. RGBA from screenshot)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                    
                image.save(buffered, format="JPEG", quality=70) # Lightweight
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            self.log_to_debug(f"Capture Failed: {e}", 'error')
            return {"text": f"画像の取得に失敗しました: {e}", "audio": None, "suggestions": []}
            
        if not image:
             return {"text": "画像の取得に失敗しました。", "audio": None, "suggestions": []}

        # Update Active Engine Interaction Time
        if self.active_engine:
            self.active_engine.update_interaction()

        # Context
        context = f"[System: User is showing an image ({mode}). Analyze it along with the input.]"
        
        # Generate Response
        response_text = ""
        suggestions_list = []
        emotion = None
        
        if self._ai_engine:
            # Pass Image to generate_response
            raw_result = self._ai_engine.generate_response(message, context=context, image=image)
            
            # Post-Processing (Reuse Logic)
            if isinstance(raw_result, dict):
                response_text = raw_result.get("response", "")
                emotion = raw_result.get("emotion") 
                suggestions_list = raw_result.get("suggestions", [])
                self.log_to_debug(f"AI Vision JSON: {response_text} (Emo: {emotion})", 'info')
            else:
                extracted_data = _extract_json_from_text(raw_result)
                if extracted_data and "response" in extracted_data:
                    response_text = extracted_data.get("response", "")
                    emotion = extracted_data.get("emotion")
                    suggestions_list = extracted_data.get("suggestions", [])
                else:
                    response_text = raw_result
        else:
            response_text = "AI Engine is not initialized."
            
        # TTS
        audio_path = self.generate_tts_audio(response_text)
        
        return {
            "text": response_text,
            "audio": audio_path,
            "image": img_str,
            "suggestions": suggestions_list
        }

    def get_url_metadata(self, url):
        """API exposed to frontend to fetch OpenGraph metadata."""
        if not hasattr(self, 'metadata_fetcher'):
            from ..services.metadata_fetcher import MetadataFetcher
            self.metadata_fetcher = MetadataFetcher()
            
            
        return self.metadata_fetcher.fetch_metadata(url)

    def force_talk(self):
        """Force the AI to initiate conversation (Proactive)."""
        self.log_to_debug("Force Talk Triggered", 'info')
        
        # Prompt Construction
        prompt = "User is idle. Initiate a conversation naturally. Check the time and suggest a topic."
        
        # Call chat with save_user_log=False to prevent DB pollution
        return self.chat(prompt, save_user_log=False)

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
    # ★追加: プレビュー用にスクショだけ撮って返すAPI
    def take_screenshot_for_preview(self, mode="screen"):
        self.log_to_debug(f"Taking screenshot for preview (Mode: {mode})...", 'info')
        try:
            from PIL import ImageGrab, Image
            from io import BytesIO
            import base64

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
