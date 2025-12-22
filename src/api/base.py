import sys
import re
import random

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
            # JSON Dump ensures safe string escaping for JS
            safe_msg = json.dumps(str(msg))
            safe_type = json.dumps(type)
            # safe_msg includes quotes, so we don't need to add them in f-string
            self._window.evaluate_js(f"logToDebug({safe_msg}, {safe_type})")

    
    def log_to_mind(self, msg):
        """Log AI thought process to the Mind tab with Persona translation."""
        import json
        import re

        # --- Mind Translation Logic ---
        translated_msg = msg
        
        # 1. Input Analysis
        if "Targeting Model:" in msg:
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
        """Play a random filler sound and log to Mind tab for immediate feedback."""
        fillers = [
            "んー、そうねぇ…",
            "えっとね…",
            "ふふっ、それはね…",
            "あ、それって…",
            "ん〜、考えさせてね…"
        ]
        chosen_filler = random.choice(fillers)
        
        # 1. Visual Feedback (Mind Tab)
        self.log_to_mind(f"(Filler) {chosen_filler} 💭")
        
        # 2. Audio Feedback (Future: Play actual WAV)
        # file_path = f"assets/voice/filler_{random.randint(1,5)}.wav"
        # self.play_sound(file_path)
        
        # For now, just a console log on frontend to verify trigger
        if self._window:
            self._window.evaluate_js(f"console.log('🔊 Playing Filler: {chosen_filler}')")
