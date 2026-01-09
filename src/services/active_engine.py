import threading
import time
import logging
import random
import os
from .news_collector import NewsCollector
from .vision_service import vision_service
from .dify_client import DifyClient
from PIL import ImageGrab

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActiveEngine:
    def __init__(self, ai_engine, on_message_callback, log_callback=None, bubble_service=None):
        self.ai_engine = ai_engine
        self.on_message_callback = on_message_callback
        self.log_callback = log_callback
        self.dify_client = None # Initialized in configure
        self.bubble_service = bubble_service # Injected dependency
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
        # Default Proactive Settings
        # work: Code, IDE
        # media: YouTube, Music
        # social: SNS, Chat
        # health: Late night checks
        # game: Gaming (New)
        self.scan_targets = ['work', 'media', 'social', 'health', 'game']

    def set_bubble_service(self, service):
        """ dependency injection setter """
        self.bubble_service = service

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

            # Dify Client Init
            dify_key = settings.get('dify_api_key', "")
            if not dify_key:
                # Fallback for Development (Verify key from script)
                dify_key = "app-drlsmEcN9o1qJTxJyJzQtbIz"
                logger.info("ActiveEngine: Using Dev Dify Key.")

            if dify_key:
                # Initialize with log callback pointing to _send_log
                self.dify_client = DifyClient(
                    api_key=dify_key, 
                    log_callback=lambda msg: self._send_log(msg, "info", "sys")
                )
                logger.info("ActiveEngine: DifyClient initialized.")
            
            # --- Vision Service Init (Inject Key from Config) ---
            api_key = settings.get('api_key')
            if api_key:
                vision_service.configure(api_key)
                logger.info("ActiveEngine: VisionService Configured with API Key.")
            else:
                logger.warning("ActiveEngine: No API Key found for VisionService.")
            # ----------------------------------------------------

        except Exception as e:
            logger.error(f"Failed to configure ActiveEngine: {e}")

    def force_dify_workflow(self, tag="AI"):
        """Manually trigger Dify Workflow."""
        threading.Thread(target=self._run_dify_workflow, args=(tag,), daemon=True).start()

    def _run_dify_workflow(self, tag):
        if not self.dify_client:
             self._send_log("Dify Client not ready.", "warning", "sys")
             return

        self._send_log(f"Triggering Dify Search (Tag: {tag})...", "info", "sys")
        try:
            result = self.dify_client.fetch_note_article(tag)
            if result:
                msg = result.get('message', '')
                url = result.get('url', '')
                
                logger.info(f"[Dify] Received: {msg} (URL: {url})")

                # Strategy Change: Use SoulBubble for Proposal
                if self.bubble_service:
                    import time
                    action_id = f"DIFY_{int(time.time())}"
                    
                    # 1. Bubble Injection (Visual Discovery)
                    packet = {
                        "category": "topics",
                        "text": f"Dify新着: {msg[:20]}...",
                        "action_id": action_id,
                        "metadata": {
                            "url": url,
                            "full_content": msg
                        },
                        "type": "discovery" 
                    }
                    self.bubble_service._active_bubbles[action_id] = packet
                    self._send_log(f"Generated Dify Bubble: {action_id}", "info", "sys")
                    
                    # Push Bubble to UI (if supported by Main callback handling)
                    bubble_payload = {
                        "type": "bubble",
                        "category": "topics",
                        "text": f"Dify: {msg[:15]}...",
                        "action_id": action_id,
                        "metadata": {"url": url}
                    }
                    import json
                    if self.on_message_callback:
                        self.on_message_callback(json.dumps(bubble_payload, ensure_ascii=False))

                    # 2. ★ Speech Generation with Prefixes (Rich Interaction)
                    # Dify由来の発話であることを演出するための導入句
                    prefixes = [
                        "ねえねえ、Difyちゃんが教えてくれたんだけど...",
                        "ネットの海で拾ってきた情報なんだけど...",
                        "リサーチ完了！ こんな記事見つけたわ。",
                        "ちょっとこれ見て！ 面白そうなの見つけたよ。",
                        "外部脳からの受信データよ。これ、興味ある？"
                    ]
                    prefix = random.choice(prefixes)
                    spoken_text = f"{prefix} {msg}"

                    # Construct Speech Payload
                    # Using 'chat' or 'proactive' type to trigger TTS and Text rendering
                    speech_payload = {
                        "text": spoken_text,
                        "emotion": "happy",
                        "suggestions": ["もっと詳しく教えて", "ありがとう", "他の記事は？"],
                        "type": "proactive" # 'proactive' usually handled similar to chat but logs differently
                    }
                    
                    self._send_log(f"🗣️ [Dify] Speaking: {spoken_text}", "info", "mind")
                    
                    if self.on_message_callback:
                        self.on_message_callback(json.dumps(speech_payload, ensure_ascii=False))

                else:
                    logger.warning("BubbleService not linked to ActiveEngine. Falling back to Log.")
                    self._send_log(f"Got Dify Article: {msg} (No Bubble Service)", "warning", "sys")

            else:
                self._send_log("Dify returned no results.", "warning", "sys")
        except Exception as e:
            self._send_log(f"Dify Workflow Failed: {e}", "error", "sys")

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
                from src.services.window_target_manager import window_target_manager
                image = window_target_manager.get_target_image()
            except Exception as e:
                logger.error(f"Capture Error: {e}")
                image = ImageGrab.grab()
                
            if not image: return

            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
            
            # DEBUG: Save image to verify what is being seen
            try:
                debug_path = os.path.join(os.getcwd(), "debug_vision.png")
                image.save(debug_path)
                
                # Extrema check
                extrema = image.convert("L").getextrema()
                
                logger.info(f"👁️ [Vision] Debug image saved to: {debug_path}")
                logger.info(f"👁️ [Vision] Image Stats: Size={image.size}, Extrema={extrema} (0,0 is black)")
                
                if extrema == (0, 0):
                    logger.warning("👁️ [Vision] WARNING: Processed image is pure black!")
                    
            except Exception as e:
                logger.error(f"Failed to save debug image: {e}")

            # 2. Local Vision Analysis (Gemini Flash Lite)
            context_title = window_target_manager.target_title if window_target_manager.target_hwnd else "Full Screen Desktop"
            vision_text = vision_service.analyze_image(image, prompt=f"User's active window: '{context_title}'.")
            
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

game: Playing games, RPG, FPS, Steam, Unity, Unreal.

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

            # 4. Determine Category
            action_cmd = result.get('action_command', '').lower()
            category = 'other'
            
            # Priority 0: Force Game from Vision Keywords (User Request)
            vision_lower = vision_text.lower()
            game_keywords = ['game', 'play', 'rpg', 'fps', 'steam', 'arknights', 'unity', 'unreal', 'minecraft', 'apex']
            if any(k in vision_lower for k in game_keywords):
                category = 'game'
                logger.info("👁️ [Proactive] Force Category: 'game' (Keyword detected)")
            
            # Priority 1: AI Decision
            elif 'category:game' in action_cmd or 'game' in action_cmd: category = 'game'
            elif 'category:work' in action_cmd or 'work' in action_cmd: category = 'work'
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
                        
                        # --- Suggestion Padding Logic (ActiveEngine) ---
                        base_sug = result.get('suggestions', [])
                        fixed = ["もっと詳しく教えて", "他の話題について"]
                        dynamic = [s for s in base_sug if s not in fixed]

                        # Ensure 8 items
                        if len(dynamic) < 8:
                            try:
                                # We can access SuggestionEngine? Not directly linked, but can import.
                                from src.services.suggestion_engine import SuggestionEngine
                                # ActiveEngine has self.ai_engine
                                eng = SuggestionEngine(self.ai_engine)
                                
                                # Context: Use last vision text
                                hist = f"Vision Context: {vision_text}\nAI Spoke: {speak_text}"
                                # Profile? Unknown here unless we have access to user_manager via some path.
                                # ActiveEngine is init with ai_engine only? 
                                # In main.py: active_engine = ActiveEngine(ai_engine, ...)
                                profile_txt = "Unknown"
                                user_name = "あなた"
                                
                                more = eng.generate(hist, profile_txt, user_name)
                                for ms in more:
                                    if ms not in dynamic and len(dynamic) < 8:
                                        dynamic.append(ms)
                            except Exception as e:
                                logger.warning(f"Active Suggestion Padding error: {e}")
                        
                        # Fallback
                        while len(dynamic) < 8:
                            dynamic.append("...その他")

                        # Combine
                        final_10 = fixed + dynamic[:8]
                        
                        # Love Slot
                        from src.services.affection_manager import AffectionManager
                        if not any(AffectionManager.is_affectionate(s) for s in final_10):
                             love = f"❤ {AffectionManager().get_random_affection()}"
                             if len(final_10) >= 10: final_10[-1] = love
                             else: final_10.append(love)

                        payload = {
                            "text": speak_text,
                            "emotion": emotion,
                            "suggestions": final_10,
                            "type": "proactive"
                        }
                        self.on_message_callback(json.dumps(payload, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Proactive Vision Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self._log(f"⚠️ [Active] Vision Scan Failed: {e}", type='error')
        finally:
            self.scan_lock.release()
            print("DEBUG: ActiveEngine._perform_vision_scan END (Lock Released)")


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
            # --- Suggestion Padding Logic (ActiveEngine Idle) ---
            base_sug = result.get('suggestions', [])
            fixed = ["もっと詳しく教えて", "他の話題について"]
            dynamic = [s for s in base_sug if s not in fixed]

            # Ensure 8 items
            if len(dynamic) < 8:
                try:
                    from src.services.suggestion_engine import SuggestionEngine
                    eng = SuggestionEngine(self.ai_engine)
                    
                    hist = f"Context: Idle Talk Triggered.\nAI Spoke: {result.get('text', '')}"
                    profile_txt = "Unknown"
                    user_name = "あなた"
                    
                    more = eng.generate(hist, profile_txt, user_name)
                    for ms in more:
                        if ms not in dynamic and len(dynamic) < 8:
                            dynamic.append(ms)
                except Exception as e:
                    logger.warning(f"Active Idle Suggestion Padding error: {e}")
            
            # Fallback
            while len(dynamic) < 8:
                dynamic.append("...その他")

            # Combine
            final_10 = fixed + dynamic[:8]
            
            # Love Slot
            from src.services.affection_manager import AffectionManager
            if not any(AffectionManager.is_affectionate(s) for s in final_10):
                 love = f"❤ {AffectionManager().get_random_affection()}"
                 if len(final_10) >= 10: final_10[-1] = love
                 else: final_10.append(love)

            result['suggestions'] = final_10
            # -----------------------------------------------

            import json
            json_str = json.dumps(result, ensure_ascii=False)
            
            if self.on_message_callback:
                self.on_message_callback(json_str)
            
        except Exception as e:
            logger.error(f"Active Trigger Failed: {e}")
