import sys
import re
import random
import threading

class BaseApiMixin:
    """Base mixin to define expected attributes and common utilities."""
    
    def __init__(self):
        # Type hints for properties initialized in Main
        self._window = None
        self._config_manager = None
        self._ai_engine = None
        self._calendar_manager = None
        self._memory_manager = None
        self.tts_engine = None
        self.active_engine = None
        self._persona_manager = None

    def log_to_debug(self, msg, type='info'):
        """Log message to the frontend debug console."""
        print(f"[{type.upper()}] {msg}")
        if self._window:
            import json
            # Determine if 'type' is actually a category or a level
            # Frontend log() signature: (msg, type='info', category='sys')
            # Known categories: 'sys', 'rag', 'dbg', 'mind'
            # Known levels: 'info', 'warn', 'error', 'success'
            
            category = 'sys'
            level = 'info'
            
            if type in ['rag', 'mind', 'dbg', 'sys']:
                category = type
                level = 'info'
            elif type in ['warn', 'error', 'success']:
                level = type
                category = 'sys'
            else:
                # Default case (info/sys) or fallback
                level = 'info'
                category = 'sys'
                if type != 'info':
                     # If it's some other string, treat as info message? or maybe level?
                     # Let's assume passed 'type' is level if not known category.
                     level = type

            safe_msg = json.dumps(str(msg))
            safe_level = json.dumps(level)
            safe_category = json.dumps(category)
            
            self._window.evaluate_js(f"logToDebug({safe_msg}, {safe_level}, {safe_category})")

    
    def log_to_mind(self, msg):
        """Log AI thought process to the Mind tab with Persona translation."""
        import json
        import re

        # --- Mind Translation Logic ---
        translated_msg = msg
        
        # 0. Pass-through for New Structured Tags (Mind, Vision, RAG)
        if msg.startswith("[Mind]") or msg.startswith("[Vision]") or msg.startswith("[RAG]"):
            # Already formatted by AI Engine, pass through directly
            pass
        elif "Targeting Model:" in msg:
            translated_msg = "(私の頭脳、Geminiモードでフル回転させるわね✨)"
        elif "Input Analysis:" in msg:
            translated_msg = "(あなたの言葉、しっかり分析中よ…🔍)"
        elif "Context:" in msg and "chars" in msg:
            translated_msg = "(これまでの会話の流れ、ちゃんと覚えているわよ…📖)"
        
        # 2. Reasoning
        elif "Reasoning..." in msg:
            translated_msg = "(うーん、えっとね、どう伝えれば一番心に響くかしら…🤔)"
        
        # 3. TTS / System
        elif "TTS" in msg and "Time:" in msg:
             translated_msg = "(お待たせ。声を届ける準備、できたわよ 🎙️)"
        
        # 4. Other specific patterns if any
        
        print(f"[MIND] {translated_msg}")
        
        if self._window:
            safe_msg = json.dumps(str(translated_msg))
            self._window.evaluate_js(f"logToMind({safe_msg})")

    def play_filler(self):
        """Play a random filler sound and show Ghost Message in UI."""
        fillers = [
            {"text": "んー、そうねぇ…", "file": "audio/fillers/thinking_01.wav"},
            {"text": "えっと…", "file": "audio/fillers/thinking_02.wav"},
            {"text": "ふふっ、それはね…", "file": "audio/fillers/thinking_03.wav"},
            {"text": "あ、それって…", "file": "audio/fillers/thinking_04.wav"},
            {"text": "ん〜、考えさせてね…", "file": "audio/fillers/thinking_05.wav"},
            {"text": "ちょっと待ってね", "file": "audio/fillers/wait_01.wav"},
            {"text": "OK、わかったわ", "file": "audio/fillers/ack_01.wav"},
        ]
        chosen = random.choice(fillers)
        text = chosen["text"]
        audio_path = chosen["file"]
        
        # 1. Visual Feedback (Mind Tab & Ghost Message)
        self.log_to_mind(f"(Filler) {text} 💭")
        
        if self._window:
            # Show Ghost Message in Chat UI
            import json
            import os
            safe_text = json.dumps(text)
            self._window.evaluate_js(f"if(window.showGhostMessage) window.showGhostMessage({safe_text})")
            
            # 2. Audio Feedback (Threaded Playback)
            # メインスレッドのブロッキング回避のため、再生処理を別スレッド化
            def _play_thread():
                try:
                    # Fallback check (Server-side path validation)
                    # Web path: audio/fillers/xxx.mp3 -> Local: dist/audio/fillers/xxx.mp3
                    # However, we must ensure we check correct local path.
                    # Assuming dist/ is root.
                    target_local = os.path.join(os.getcwd(), "dist", audio_path.replace("/", os.sep))
                    final_path = audio_path
                    
                    if not os.path.exists(target_local):
                        self.log_to_debug(f"⚠️ [Filler] Missing: {audio_path}. Fallback to default.", 'warn')
                        final_path = "audio/fillers/thinking_02.wav" # Fallback
                        # Check fallback exists
                        fb_local = os.path.join(os.getcwd(), "dist", final_path.replace("/", os.sep))
                        if not os.path.exists(fb_local):
                             self.log_to_debug(f"❌ [Filler] Fallback also missing. Converting to visual only.", 'error')
                             return

                    self.log_to_debug(f"🔊 [Filler] Sending play command for: {text} ({final_path})", 'sys')
                    
                    # JS Promise handling for logging back to UI
                    js_code = f"""
                    new Audio('{final_path}').play()
                        .then(() => {{
                            console.log('[Filler] Playback started');
                            if(window.logToDebug) window.logToDebug('✅ [Filler] Audio started', 'success');
                        }})
                        .catch(e => {{
                            console.error('[Filler] Playback failed', e);
                            if(window.logToDebug) window.logToDebug('❌ [Filler] Audio failed: ' + e, 'error');
                        }});
                    """
                    self._window.evaluate_js(js_code)
                    
                except Exception as e:
                    self.log_to_debug(f"❌ [Filler] Thread Error: {e}", 'error')
                    print(f"[Filler] Playback Error: {e}")

            threading.Thread(target=_play_thread, daemon=True).start()

    def open_browser(self, url):
        """Opens a URL in the system's default browser."""
        import webbrowser
        self.log_to_debug(f"Opening Browser: {url}", 'info')
        try:
            webbrowser.open(url)
            return {'status': 'success'}
        except Exception as e:
            self.log_to_debug(f"Browser Open Failed: {e}", 'error')
            return {'status': 'error', 'message': str(e)}
