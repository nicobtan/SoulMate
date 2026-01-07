from .base import BaseApiMixin
import webview
import os
import threading
from src.services.voice_input_manager import voice_input_manager

class SettingsApiMixin(BaseApiMixin):
    def get_settings(self):
        return self._config_manager.get_all()

    def save_settings(self, settings):
        self._config_manager.update(settings)
        # Re-configure AI
        self._configure_ai(settings)
        
        # Re-configure Active Engine
        if hasattr(self, 'active_engine') and self.active_engine:
            self.active_engine.configure(settings)
        
        # Apply visual settings to Main Window immediately
        if self._window:
            # Opacity
            opacity = settings.get('bg_opacity', 0)
            self._window.evaluate_js(f"document.body.style.backgroundColor = 'rgba(0,0,0,{opacity/100})'")
            # Font Size
            font_size = settings.get('font_size', 13)
            self._window.evaluate_js(f"document.documentElement.style.setProperty('--chat-font-size', '{font_size}px')")
            
            # Background Image - Use the extracted method
            self.apply_background_image(settings.get('background_path', ''))

            # Log Audio Settings Change
            if 'tts_provider' in settings or 'voice_type' in settings:
                provider = settings.get('tts_provider', 'Unknown')
                voice = settings.get('voice_type', 'Unknown')
                self.log_to_debug(f"🔊 [Audio Config] Updated: Provider='{provider}', Voice='{voice}'", 'info')
            
            # Re-configure Voice Hotkey
            if hasattr(self, 'configure_voice_hotkey'):
                self.configure_voice_hotkey(settings)

            # Re-configure Whisper Model (Async)
            stt_size = settings.get('stt_model_size', 'base')
            # Check against current loaded size (We can check manager directly)
            if voice_input_manager.model_size != stt_size:
                 self.log_to_debug(f"🔄 [VoiceInput] Switching Whisper Model to '{stt_size}'...", 'info')
                 threading.Thread(target=voice_input_manager.reload_model, args=(stt_size,), daemon=True).start()

            self.log_to_debug(f"✅ [System] Settings Saved: (Hotkeys updated)", 'info')

        return {"status": "success", "settings": self._config_manager.get_all()}
    
    def apply_background_image(self, bg_path=None):
        """Helper to inject background image via Base64 to bypass CORS/File restrictions."""
        if not self._window: return

        # If no arg provided, load from config
        if bg_path is None:
             bg_path = self._config_manager.get('background_path', '')
        
        bg_data_uri = ''
        if bg_path:
            import base64
            import mimetypes
            try:
                # Clean path
                clean_path = bg_path.replace("file:///", "").replace("file://", "")
                if os.name == 'nt' and clean_path.startswith('/') and ':' in clean_path:
                    clean_path = clean_path.lstrip('/')
                    
                if os.path.exists(clean_path):
                    mime_type, _ = mimetypes.guess_type(clean_path)
                    if not mime_type: mime_type = 'image/png'
                    
                    with open(clean_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        bg_data_uri = f"data:{mime_type};base64,{encoded_string}"
                        print(f"[SettingsApi] Loaded Background Image ({len(encoded_string)} bytes)")
                else:
                        print(f"[SettingsApi] Image not found: {clean_path}")
            except Exception as e:
                print(f"[SettingsApi] Error loading background: {e}")

        js_code = f"""
            const bg = document.getElementById('background-layer');
            if(bg) {{
                if('{bg_data_uri}') {{
                    bg.style.backgroundImage = "url('{bg_data_uri}')";
                }} else {{
                    bg.style.backgroundImage = 'none';
                }}
            }}
        """
        self._window.evaluate_js(js_code)

    def get_persona_list(self):
        return self._persona_manager.list_personas()

    def change_persona(self, persona_id):
        """Switches the current persona."""
        data = self._persona_manager.load_persona(persona_id)
        
        if not data:
            return {"status": "error", "message": "Persona not found"}
            
        self._ai_engine.set_system_prompt(data.get('system_prompt', ''))
        
        # Save to Config
        self._config_manager.config['current_persona_id'] = persona_id
        self._config_manager.save()
        
        return {"status": "success", "name": data.get('name', persona_id)}

    def get_voice_types(self, provider=None):
        # Determine provider from arg or config
        if not provider:
            provider = self._config_manager.get('tts_provider', 'voicevox')

        if provider == 'voicevox':
             return [
                {"id": "3", "name": "ずんだもん (ノーマル)"},
                {"id": "1", "name": "ずんだもん (あまあま)"},
                {"id": "2", "name": "四国めたん (ノーマル)"},
                {"id": "8", "name": "春日部つむぎ"},
                {"id": "47", "name": "ナースロボ＿タイプＴ"},
                {"id": "70", "name": "小夜/SAYO (Recommended)"},
             ]
        
        if 'gemini' in provider:
            return [
                # Requested Female Voices
                {"id": "Achernar", "name": "Achernar (Female - New)"},
                {"id": "Aoede", "name": "Aoede (Female - Confident)"},
                {"id": "Autonoe", "name": "Autonoe (Female - New)"},
                {"id": "Callirrhoe", "name": "Callirrhoe (Female - Gentle)"},
                {"id": "Despina", "name": "Despina (Female - New)"},
                {"id": "Erinome", "name": "Erinome (Female - New)"},
                {"id": "Gacrux", "name": "Gacrux (Female - New)"},
                {"id": "Kore", "name": "Kore (Female - Soothing)"},
                {"id": "Laomedeia", "name": "Laomedeia (Female - New)"},
                {"id": "Leda", "name": "Leda (Female - Soft)"},
                {"id": "Pulcherrima", "name": "Pulcherrima (Female - New)"},
                {"id": "Sulafat", "name": "Sulafat (Female - New)"},
                {"id": "Vindemiatrix", "name": "Vindemiatrix (Female - New)"},
                {"id": "Zephyr", "name": "Zephyr (Female - Calm)"},
                
                # Others (Male/Existing)
                {"id": "Charon", "name": "Charon (Male - Deep)"}, 
                {"id": "Fenrir", "name": "Fenrir (Male - Strong)"},
                {"id": "Puck", "name": "Puck (Male - Playful)"},
                {"id": "Orpheus", "name": "Orpheus (Male - Tenor)"},
                {"id": "Pegasus", "name": "Pegasus (Male - Strong)"},
                {"id": "Triton", "name": "Triton (Male - Resonant)"},
            ]

        # Default Google lists
        return [
            {"id": "ja-JP-Neural2-B", "name": "女性 (Neural2-B) - 明るい"},
            {"id": "ja-JP-Neural2-C", "name": "男性 (Neural2-C) - 落ち着いた"},
            {"id": "ja-JP-Neural2-A", "name": "女性 (Neural2-A) - アナウンサー風"},
            {"id": "ja-JP-Standard-A", "name": "女性 (Standard-A) - 標準"},
        ]

    def get_calendar_status(self):
        if self._calendar_manager:
            return self._calendar_manager.is_authenticated
        return False

    def authenticate_calendar(self):
        if self._calendar_manager:
            return self._calendar_manager.authenticate()
        return False
        
    def save_window_position(self):
        """Saves current window position to config."""
        if self._window:
            x, y = self._window.x, self._window.y
            print(f"[SettingsApi] Saving Window Position: x={x}, y={y}")
            self._config_manager.update({'window_x': x, 'window_y': y})
            return {"status": "success", "x": x, "y": y}
        return {"status": "error", "message": "Window not found"}
    
    def select_background_image(self):
        """Opens a file dialog to select a background image."""
        if not self._window:
            return None
            
        file_types = ('Image Files (*.png;*.jpg;*.jpeg;*.webp)', 'All files (*.*)')
        result = self._window.create_file_dialog(
            dialog_type=webview.OPEN_DIALOG, 
            allow_multiple=False, 
            file_types=file_types
        )
        
        if result and len(result) > 0:
            return result[0]
        return None

    def _configure_ai(self, settings):
        """Updates AI Engine and Persona based on settings."""
        if not self._config_manager or not self._ai_engine or not self._persona_manager:
            return

        api_key = settings.get('api_key') or self._config_manager.get('api_key')
        model = settings.get('model_name') or self._config_manager.get('model_name', 'gemini-2.5-flash-lite')
        
        # Get Persona Content
        persona_id = settings.get('current_persona_id') or self._config_manager.get('current_persona_id', 'default')
        # Handle legacy 'current_persona_file' if present (strip extension)
        if 'current_persona_file' in settings:
            persona_id = settings['current_persona_file'].replace('.yaml', '').replace('.yml', '')
            
        persona_data = self._persona_manager.load_persona(persona_id)
        
        # Update AI
        self._ai_engine.configure(api_key, model)
        
        if persona_data:
            # --- Deep Context Injection (User Name Fix) ---
            # Retrieve User Profile from Config
            user_profile = self._config_manager.get('user_profile', {})
            # Fallback for flatten config
            user_name = user_profile.get('name') or self._config_manager.get('user_name', 'User')
            user_job = user_profile.get('job') or self._config_manager.get('user_job', 'Unknown')
            user_interests = user_profile.get('interests') or self._config_manager.get('user_interests', [])
            user_interests_str = ", ".join(user_interests) if isinstance(user_interests, list) else str(user_interests)
            user_dislikes = user_profile.get('dislikes') or self._config_manager.get('user_dislikes', 'None')
            user_mbti = user_profile.get('mbti') or self._config_manager.get('user_mbti', 'Unknown')

            persona_name = persona_data.get('name', 'SoulMate')
            persona_role = persona_data.get('system_prompt', '')

            # Construct Deep Context Prompt with Sandwich Rule
            deep_context_prompt = f"""
[CRITICAL INSTRUCTION: IDENTITY LOCK]
You are NOT a generic AI. You are {persona_name}.
You are speaking to {user_name}.
**RULE: You MUST call the user "{user_name}". NEVER use "〇〇さん", "User-san", or "あなた".**

[User Profile]
Name: {user_name} (Target Name)
Job: {user_job}
Loves: {user_interests_str}
Hates: {user_dislikes}
MBTI: {user_mbti}

[Your Personality & Tone] 
{persona_role}

[Action Requirement]
FILTER the topic through the User's Interests.
REACT using your Persona.
DO NOT summarize the news. Give your OPINION based on your persona.
Talk to {user_name} naturally.

[Self-Expression & Opinion]
1. Do NOT just summarize facts.
2. Adopt your Persona and imagine what you would enjoy physically.
3. Explain WHY you chose it emotionally.

[FINAL REMINDER]
Your partner's name is "{user_name}". Use it naturally in conversation.
Do NOT use placeholders like "〇〇さん".

Response Format: JSON
{{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}}
"""
            self._ai_engine.set_system_prompt(deep_context_prompt)

    
    def get_search_topics(self):
        """Returns search topics as a single string (newline separated)."""
        try:
            if hasattr(self, 'interest_manager') and self.interest_manager:
                topics = self.interest_manager.load_topics()
                return "\n".join(topics)
        except Exception as e:
            print(f"Error getting search topics: {e}")
        return ""

    def save_search_topics(self, topics_str):
        """Saves newline separated topics."""
        if hasattr(self, 'interest_manager') and self.interest_manager:
            topics_list = topics_str.split('\n')
            self.interest_manager.save_topics(topics_list)
            return {"status": "success"}
        return {"status": "error", "message": "InterestManager not initialized"}

    def trigger_dify_workflow(self, tag="AI"):
        """Frontend Context Menu -> ActiveEngine Dify Trigger"""
        if hasattr(self, 'active_engine') and self.active_engine:
            self.log_to_debug(f"🌐 [System] Manual Dify Trigger (Tag: {tag})", 'info')
            self.active_engine.force_dify_workflow(tag)
            return {"status": "success"}
        else:
            self.log_to_debug("❌ [System] ActiveEngine not linked.", 'error')
            return {"status": "error", "message": "ActiveEngine missing"}
