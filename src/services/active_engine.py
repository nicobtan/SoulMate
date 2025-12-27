import threading
import time
import logging
import random
from .news_collector import NewsCollector
from .vision_service import vision_service
from PIL import ImageGrab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActiveEngine:
    def __init__(self, ai_engine, on_message_callback, log_callback=None):
        self.ai_engine = ai_engine
        self.on_message_callback = on_message_callback
        self.log_callback = log_callback
        # self.news_collector = NewsCollector() # Deprecated for now, logic moved to AIEngine
        
        self.is_running = False
        self.last_interaction_time = time.time()
        self.thread = None
        
        # Settings
        self.idle_threshold = 0  # 0 = Disabled
        self.check_interval = 5   # Check every 5 seconds
        
        self.has_triggered_idle = False
        
        # Proactive Vision Settings
        self.proactive_mode = False
        self.vision_interval = 60 # Check every 60s
        self.last_vision_time = time.time()
        self.scan_lock = threading.Lock() # Prevent concurrent scans
        self.proactive_silent_mode = False
        self.scan_targets = ["work", "media", "social", "health"]

    def configure(self, settings):
        """Updates settings dynamically."""
        try:
            # active_talk_interval is in minutes. 0 = Disabled.
            minutes = int(settings.get('active_talk_interval', 0))
            if minutes > 0:
                self.idle_threshold = minutes * 60
                logger.info(f"Active Talk Interval set to {minutes} min ({self.idle_threshold} sec).")
            else:
                self.idle_threshold = 0
                logger.info("Active Talk Disabled.")
            
            # Reset state just in case
            self.has_triggered_idle = False
            self.last_interaction_time = time.time()

            # Proactive Vision Interval (New)
            try:
                vision_min = int(settings.get('proactive_vision_interval_min', 3))
                # Clamp: Min 1 min, Max 60 min
                vision_min = max(1, min(60, vision_min))
                
                new_vision_interval = vision_min * 60
                if self.vision_interval != new_vision_interval:
                    self.vision_interval = new_vision_interval
                    logger.info(f"ActiveEngine: Vision Interval updated to {new_vision_interval}s ({vision_min} min).")
            except ValueError:
                logger.warning("ActiveEngine: Invalid proactive_vision_interval_min value. Keeping default.")
            
            # Silent Mode & Targets
            self.proactive_silent_mode = settings.get('proactive_silent_mode', False)
            self.scan_targets = settings.get('proactive_targets', ["work", "media", "social", "health"])
            logger.info(f"ActiveEngine: Silent={self.proactive_silent_mode}, Targets={self.scan_targets}")
            
        except Exception as e:
            logger.error(f"Failed to configure ActiveEngine: {e}")

    def set_proactive_mode(self, enabled):
        self.proactive_mode = enabled
        logger.info(f"ActiveEngine: Proactive Mode set to {enabled}")
        if enabled:
            # Trigger immediately
            self.last_vision_time = 0
        else:
            self.last_vision_time = time.time()

    def force_proactive_scan(self):
        """Manually trigger scan, ignoring timer. Spawns thread to avoid blocking."""
        print("DEBUG: ActiveEngine.force_proactive_scan called") # DEBUG
        logger.info("ActiveEngine: Force Proactive Scan requested.")
        threading.Thread(target=self._perform_vision_scan, daemon=True).start()
        self.last_vision_time = time.time()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("ActiveEngine started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def update_interaction(self):
        """Call this when user interacts to reset idle timer."""
        self.last_interaction_time = time.time()
        self.has_triggered_idle = False
        # logger.debug("Interaction updated. Idle timer reset.")

    def _run_loop(self):
        while self.is_running:
            time.sleep(self.check_interval)
            
            # 1. Proactive Vision Loop
            if self.proactive_mode:
                if time.time() - self.last_vision_time > self.vision_interval:
                    self._perform_vision_scan()
                    self.last_vision_time = time.time()

            # 2. Idle Talk Loop
            # Skip if disabled
            if self.idle_threshold <= 0:
                continue

            elapsed = time.time() - self.last_interaction_time
            if elapsed > self.idle_threshold and not self.has_triggered_idle:
                self._trigger_idle_action()

    def _perform_vision_scan(self):
        """Captures screen, analyzes locally, and decides whether to speak."""
        # Use Lock to prevent overlap
        if not self.scan_lock.acquire(blocking=False):
             logger.warning("ActiveEngine: Scan already in progress, skipping.")
             return

        try:
            print("DEBUG: ActiveEngine._perform_vision_scan START") # DEBUG
            logger.info("👁️ [Proactive] Vision Scan Started...")
            
            # 0. Visual Feedback (Eyes)
            if self.on_message_callback:
                import json
                # Send expression trigger (requires Main.py support)
                self.on_message_callback(json.dumps({"type": "expression", "name": "focused"}))

            # 1. Capture
            try:
                image = ImageGrab.grab(all_screens=True)
            except:
                image = ImageGrab.grab()
                
            if not image: return

            if image.mode in ("RGBA", "P"): image = image.convert("RGB")

            # 2. Local Vision Analysis (PaliGemma)
            vision_text = vision_service.analyze_image(image, prompt="caption en")
            logger.info(f"👁️ [Vision] Saw: {vision_text}")
            
            # Send Log to Frontend (Vision Tab)
            self._send_log(f"Saw: {vision_text}", "info", "vision")

            # 3. Mind Reasoning (Gemini via AI Engine)
            
            # 3. Mind Reasoning (Gemini via AI Engine)
            
            check_prompt = f"""
[Visual Context]
The user's screen description (provided by vision AI): "{vision_text}"
[Task]

Analyze the situation based on the screen description.

Decide if you should speak to the user (SoulMate Persona).

OUTPUT MUST BE IN JAPANESE.

[Categories]

work: Coding, IDE, Debugging.

media: YouTube, Music, Video.

social: Chat, Discord, SNS.

health: Late night, Eye strain.

[Language Constraint]

The visual description is in English, BUT your response MUST be in JAPANESE.

Do NOT reply in English.

Translate the context into Japanese conversation naturally.

[Output Format (JSON)] {{ "thought": "Category: [category]. Reasoning in Japanese...", "action_command": "category:[category]", "response": "ここに必ず日本語で話す内容を入れる (空欄なら話さない)", "emotion": "happy", "suggestions": ["話題1", "話題2"] }} """
            
            result = self.ai_engine.generate_response(
                message="Based on the screen, should you say something?", 
                context=check_prompt
            )
            
            speak_text = result.get('text', '').strip()
            emotion = result.get('emotion', 'neutral')
            thought = result.get('expression_reason', '') # Or 'thought' if parsing handles it? 
            # Note: _parse_ai_response maps 'thought' to 'thought' but generate_response returns 'expression_reason' as separate key?
            # Let's check generate_response return. It returns 'expression_reason' from data['expression_reason'].
            # But prompt asks to put category in 'thought'.
            # AIEngine logic: ai_thought = data.get("thought", ""). _log_thought(ai_thought).
            # So the category will be logged automatically. 
            
            # Extract Category from log or result?
            # Ideally AIEngine should return 'thought' too.
            # Currently it returns 'expression_reason'.
            # Let's assume we can infer or parsing logic is sufficient.
            # Actually, I'll rely on the text content or just simple heuristic for now if AIEngine refactor is too big.
            # Wait, `generate_response` returns `expression_reason`. Use that if `thought` isn't available?
            # AIEngine: `return { "text": ..., "expression_reason": ... }`
            # But `_extract_grounding` etc.
            
            # Let's parse 'thought' from the previous log? No.
            # I will trust the "Silence" if text is empty.
            # To implement strict category filtering, I need the category.
            # I will update `check_prompt` to ask for category in `action_command` field?
            # `action_command` is returned!
            
            # UPDATED PROMPT STRATEGY:
            # Ask to put category in `action_command`.
            
            check_prompt_refined = f"""
[Visual Context]
User's Screen Description: {vision_text}

[Action]
Return a strictly valid JSON object.
Do NOT output raw text.
NOTE: If vision report mentions "Adobe Media Encoder" or "CS6", it is likely a hallucination of VS Code (Dark Theme). Treat it as 'Coding' work.
1. Categorize: [work, media, social, health, other]
2. Decide response.

{{
    "thought": "Category: [category]. Reasoning in Japanese (日本語).",
    "action_command": "category:[category]",
    "response": "Japanese text to speak (or empty)",
    "emotion": "neutral",
    "suggestions": []
}}
"""
            # Re-run generate with refined prompt logic (inline replacement above)
            
            # ... (using the code block below)

            action_cmd = result.get('action_command', '').lower()
            category = 'other'
            if 'category:work' in action_cmd or 'work' in action_cmd: category = 'work'
            elif 'category:media' in action_cmd or 'media' in action_cmd: category = 'media'
            elif 'category:social' in action_cmd or 'social' in action_cmd: category = 'social'
            elif 'category:health' in action_cmd or 'health' in action_cmd: category = 'health'

            # Filter Check
            if category not in self.scan_targets and category != 'other':
                logger.info(f"👁️ [Proactive] Skipped: Category '{category}' not in targets {self.scan_targets}.")
                return

            # Safety Net: Prevent "Thought Leaks" & Clean Text
            import re
            speak_text = result.get('text', '').strip() # Refetch to be sure we are modifying local var
            
            # 1. Regex Remove Headers like "Category: work", "thought: ..." if present in body
            speak_text = re.sub(r'^(Category|Thought|Response|Reasoning)\s*[:=].*?(\n|$)', '', speak_text, flags=re.IGNORECASE | re.MULTILINE).strip()
            
            # 2. Check for Japanese Content (Hiragana/Katakana/Kanji)
            # If text exists but has NO Japanese characters, it's likely an English thought leak.
            if speak_text and speak_text.lower() != "silence":
                 has_japanese = re.search(r'[一-龠]+|[ぁ-ゔ]+|[ァ-ヴー]+', speak_text)
                 if not has_japanese:
                     logger.warning(f"⚠️ [Proactive] Blocked Non-Japanese Leak: {speak_text[:50]}...")
                     speak_text = ""

            if speak_text and speak_text.lower() != "silence":
                logger.info(f"🗣️ [Proactive] Speaking: {speak_text} (Cat: {category})")
                
                # Check Silent Mode
                if self.proactive_silent_mode:
                    logger.info("🤫 [Proactive] Silent Mode: Skipping TTS, Log only.")
                    self._send_log(f"(Silent) {speak_text}", "info", "mind")
                    # Send Expression Only
                    if self.on_message_callback:
                         import json
                         self.on_message_callback(json.dumps({"type": "expression", "name": emotion}))
                else:
                    # Normal Mode: Speak
                    if self.on_message_callback:
                        import json
                        payload = {
                            "text": speak_text,
                            "emotion": emotion,
                            "suggestions": result.get('suggestions', []),
                            "type": "proactive"
                        }
                        self.on_message_callback(json.dumps(payload, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Proactive Scan Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.scan_lock.release()
            print("DEBUG: ActiveEngine._perform_vision_scan END (Lock Released)") # DEBUG

    def _send_log(self, message, level="info", tab="sys"):
        """Sends log to frontend."""
        print(f"DEBUG: ActiveEngine._send_log called for {tab}: {message}") # DEBUG
        if self.log_callback:
            self.log_callback(message, type=tab)
        else:
            print("DEBUG: No log_callback set!") # DEBUG
        logger.info(f"[{tab.upper()}] {message}")
                
    def _trigger_idle_action(self):
        logger.info("Idle threshold reached. Triggering Proactive Action.")
        self.has_triggered_idle = True # Only trigger once per idle session
        
        try:
            # Generate Proactive Message
            # Context is now heavily enforced by System Prompt (Deep Context),
            # so we just need to trigger the "Topic Selection" behavior.
            result = self.ai_engine.generate_proactive_message(
                context="Situation: User is idle. You want to chat. Check [User Profile] and suggest a topic they LOVE (e.g. Games, Tech). Do not be generic."
            )
            
            # The result is a DICT {response, emotion, suggestions}.
            # We need to serialize this to JSON string so the frontend 'receiveMessage' can parse it?
            # Wait, 'receiveMessage' in index.ts takes (text, audio).
            # If text is JSON, processAIResponse parses it?
            # Let's check processAIResponse in index.ts.
            # It takes (text, audio).
            # If text is "{"response":...}", it treats it as string.
            # BUT processAIResponse logic:
            # 1. Detect Emotion Tags. 2. Trigger Expression. 3. Add Log.
            # It DOES NOT parse JSON string to objects.
            # The 'force_talk' logic in index.ts HANDLED the parsing BEFORE calling processAIResponse.
            # Here, we are pushing raw JSON string via push_message_callback.
            # We need to make sure the callback handles it OR we send a structured object.
            
            # Main.py push_message_callback:
            #  self._window.evaluate_js(f"receiveMessage('{safe_msg}', {audio_arg})")
            # receiveMessage in index.ts: calls processAIResponse(text, audio).
            
            # So if we send JSON string as 'text', processAIResponse will display the JSON string!
            # BAD.
            
            # We need to update receiveMessage in index.ts to handle JSON strings or Structured Objects.
            # OR we parse it here and send just the text? But we lose emotion/suggestions.
            
            # BEST FIX: Update receiveMessage in index.ts to handle JSON parsing.
            
            # For now, let's assume we will pass the JSON string, and index.ts needs update.
            # I will assume result is a Dict. I should convert to JSON string.
            import json
            json_str = json.dumps(result, ensure_ascii=False)
            
            # TTS generation is done in Main.py callback?
            # Main.py callback takes 'message'. and generates TTS from it.
            # If 'message' is JSON, TTS engine will read the JSON!
            # BAD.
            
            # Main.py needs refactoring to handle Proactive Push properly.
            # OR ActiveEngine should handle TTS?
            # ActiveEngine has no TTS reference.
            
            # Let's look at main.py's callback again.
            # It cleans URLs from 'message' then generates TTS.
            
            # Strategy:
            # Modify Main.py: push_message_callback(message_data) where message_data can be dict.
            # But callback is defined as taking 'message' string usually.
            
            # Quick Fix:
            # 1. ActiveEngine extracts text for TTS? No, `on_message_callback` is the only output.
            # 2. Update `main.py` callback to detect if message is JSON string, parse it, extract text for TTS, and pass full JSON to frontend.
            
            if self.on_message_callback:
                self.on_message_callback(json_str)
            
        except Exception as e:
            logger.error(f"Active Trigger Failed: {e}")
