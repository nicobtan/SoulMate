import os
import threading
import webbrowser
import re
import json
from .base import BaseApiMixin
from .json_helper import _extract_json_from_text
from PIL import ImageGrab

class ChatApiMixin(BaseApiMixin):
    
    def verify_api_key(self, api_key):
        if self._ai_engine:
            return self._ai_engine.configure(api_key) is not None
        return False

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


    def chat(self, message, save_user_log=True):
        """Sends a message to the AI Engine and returns the response object {text, audio}."""
        # Log input
        self.log_to_debug(f"Chat Received: {message}", 'info')

        # Update Active Engine Interaction Time
        if self.active_engine:
            self.active_engine.update_interaction()

        # Retrieve Context (RAG)
        context = ""
        # 0. User Profile Context (Dynamic Injection for Amnesia Fix)
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
            
            # Fetch events if authenticated
            if self._calendar_manager.is_authenticated:
                events = self._calendar_manager.get_upcoming_events(max_results=20)
                events_str = "\n".join(events)
                calendar_context = f"\n[System Data: User's Upcoming Schedule]\n{events_str}\n"
                context += calendar_context
            else:
                 # If not authenticated... (keep existing auth logic)
                 if "予定" in message or "schedule" in message.lower():
                      def auth_callback(msg, type):
                           if type == 'auth_url':
                               user_msg = f"認証が必要です: {msg}"
                               if self._window:
                                   safe = user_msg.replace("'", "\\'").replace("\n", "\\n")
                                   self._window.evaluate_js(f"receiveMessage('{safe}', null)")
                           else:
                               self.log_to_debug(msg, type)

                      threading.Thread(target=self._calendar_manager.authenticate, args=(auth_callback,), daemon=True).start()

        # Generate Response
        response_text = ""
        suggestions_list = []
        emotion = None
        
        if self._ai_engine:
            raw_result = self._ai_engine.generate_response(message, context=context)
            
            # Check if JSON dict or String
            if isinstance(raw_result, dict):
                response_text = raw_result.get("response", "")
                emotion = raw_result.get("emotion") 
                suggestions_list = raw_result.get("suggestions", [])
                self.log_to_debug(f"AI JSON: {response_text} (Emo: {emotion})", 'info')
            else:
                # String response - Try robust extraction
                extracted_data = _extract_json_from_text(raw_result)
                
                if extracted_data and "response" in extracted_data:
                    # Extraction Success
                    response_text = extracted_data.get("response", "")
                    emotion = extracted_data.get("emotion")
                    suggestions_list = extracted_data.get("suggestions", [])
                    self.log_to_debug(f"AI JSON (Extracted): {response_text}", 'info')
                else:
                    # Extraction Failed - Fallback logic
                    # If text contains '{', it might be broken JSON. Split and take pre-JSON part.
                    if '{' in raw_result:
                        response_text = raw_result.split('{')[0].strip()
                        self.log_to_debug(f"AI Text (Fallback Split): {response_text}", 'warn')
                    else:
                        response_text = raw_result
                        self.log_to_debug(f"AI Text: {response_text}", 'info')
        else:
            response_text = "AI Engine is not initialized."

        # DB Saving (Desktop App Logic)
        from src import core_instance
        db = core_instance.get_db()
        if db:
            active = db.get_active_session()
            session_id = active['id'] if active else db.create_session()
            
            # Save User (Only if flag is True)
            if save_user_log:
                db.add_message(session_id, "user", message)
            
            # Save AI
            meta = {"suggestions": suggestions_list}
            db.add_message(session_id, "ai", response_text, meta=meta)

        # ... (rest of logic) ...
        
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
                    # ★修正: 今回のやり取りだけでなく、直近の数ターンを含めて要約する
                    # 履歴を取得 (今保存した分も含めて最新5件程度)
                    recent_msgs = db.get_messages(session_id)[-6:]
                    
                    context = ""
                    for m in recent_msgs:
                         if not m['content'].startswith('['):
                            context += f"{m['role']}: {m['content']}\n"
                    
                    # AI生成
                    if self._ai_engine:
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
        """Captures a screenshot or clipboard and sends it with the message to the AI Engine."""
        self.log_to_debug(f"Vision Chat Received: {message} Mode: {mode}", 'info')
        
        # Capture Logic
        image = None
        img_str = None
        
        try:
            if mode == "clipboard":
                # Windows: grabclipboard() returns Image or list of filenames
                image = ImageGrab.grabclipboard()
                if image is None:
                    return {
                        "text": "クリップボードに画像が見当たりません。\nWin+Shift+S (領域指定) や Alt+PrtSc (ウィンドウ) でコピーしてから、もう一度右クリックしてください。", 
                        "audio": None, 
                        "suggestions": []
                    }
                if isinstance(image, list):
                    # Handle file paths in clipboard
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
    def get_sessions(self, limit=50):
        """Returns list of sessions from DB."""
        from src import core_instance
        db = core_instance.get_db()
        if db:
            # Row objects to dict
            sessions = db.get_sessions(limit)
            return [dict(s) for s in sessions]
        return []

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
