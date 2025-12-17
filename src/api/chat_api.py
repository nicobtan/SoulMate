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
            # VoiceService Check (VOICEVOX or Gemini)
            if provider in ['voicevox', 'gemini'] and getattr(self, 'voice_service', None):
                 # For Gemini, we trust validation is done in VoiceService or Settings
                 return self.voice_service.generate_voice(tts_text.strip(), voice_name=voice_name, provider=provider)
            
            # Google Fallback
            elif getattr(self, 'tts_engine', None):
                 if provider == 'google' and len(str(voice_name)) < 3:
                     voice_name = 'ja-JP-Neural2-B'
                     
                 return self.tts_engine.generate_voice(
                    tts_text, 
                    output_dir=os.path.join(base_dir, 'dist/audio'), 
                    voice_name=voice_name
                )
        except Exception as e:
            self.log_to_debug(f"TTS Error: {e}", 'error')
            return None


    def chat(self, message):
        """Sends a message to the AI Engine and returns the response object {text, audio}."""
        # Log input
        self.log_to_debug(f"Chat Received: {message}", 'info')

        # Update Active Engine Interaction Time
        if self.active_engine:
            self.active_engine.update_interaction()

        # Retrieve Context (RAG)
        context = ""
        if self._memory_manager:
            context = self._memory_manager.retrieve_context(message)
            
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
        
        return {
            "text": response_text,
            "audio": audio_path,
            "suggestions": suggestions_list
        }

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
        
        if self.active_engine:
            self.active_engine.update_interaction()
            
        # Context (Context retrieval might be less relevant if user didn't say anything, but Time is handled in Engine)
        # We can pass empty context or last known context? Engine handles Time.
        
        response_text = ""
        suggestions_list = []
        emotion = None
        audio_path = None
        
        if self._ai_engine:
            # Call Proactive Generation
            raw_result = self._ai_engine.generate_proactive_message()
            
            # Use same processing logic as Chat (Simplified Copy)
            if isinstance(raw_result, dict):
                response_text = raw_result.get("response", "")
                emotion = raw_result.get("emotion")
                suggestions_list = raw_result.get("suggestions", [])
                self.log_to_debug(f"AI Proactive JSON: {response_text}", 'info')
            else:
                # String response - Try robust extraction
                extracted_data = _extract_json_from_text(raw_result)
                
                if extracted_data and "response" in extracted_data:
                    # Extraction Success
                    response_text = extracted_data.get("response", "")
                    emotion = extracted_data.get("emotion")
                    suggestions_list = extracted_data.get("suggestions", [])
                    self.log_to_debug(f"AI Proactive JSON (Extracted): {response_text}", 'info')
                else:
                    # Extraction Failed - Fallback logic
                    if '{' in raw_result:
                        response_text = raw_result.split('{')[0].strip()
                        self.log_to_debug(f"AI Proactive Text (Fallback Split): {response_text}", 'warn')
                    else:
                        response_text = raw_result
                        self.log_to_debug(f"AI Proactive Text: {response_text}", 'info')
        else:
            response_text = "AI Engine is not initialized."

        # Memory Log (System Trigger)
        if self._memory_manager and self._config_manager:
            current_persona = self._config_manager.get('current_persona_file', 'default')
            self._memory_manager.log_interaction("[System:ForceTalk]", response_text, current_persona)
            
        # TTS
        audio_path = self.generate_tts_audio(response_text)
        
        # Static Suggestion
        suggestions_list.append("別の話題はある？")
        
        return {
            "text": response_text,
            "audio": audio_path,
            "suggestions": suggestions_list
        }

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
