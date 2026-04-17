import threading
import time
import logging
import random
import os
from src.services.content.news_collector import NewsCollector
from src.services.vision.vision_service import vision_service
from src.services.external.dify_client import DifyClient
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
        self.ears = None # Injected SoulMateEars
        self.hearing_active = False # Continuous Listening Flag
        # self.news_collector = NewsCollector() # Deprecated for now, logic moved to AIEngine
        
        self.is_running = False
        self.stealth_mode = False
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

    def set_stealth_mode(self, enabled):
        self.stealth_mode = enabled
        logger.info(f"ActiveEngine: Stealth Mode set to {enabled}")
        # When in stealth mode, we override AIEngine system prompt for background OS work
        if self.stealth_mode and self.ai_engine:
            stealth_prompt = "現在あなたはステルスモードでバックグラウンド稼働中です。音声や表示は使えません。ユーザーの作業を邪魔せず、OS操作や情報収集、記録などを優先してください。(Gemini 3.1 Pro)"
            import json
            # We use the existing update logic via context injection
            self.ai_engine.set_system_prompt(stealth_prompt)

    def configure(self, settings):
        """Updates settings dynamically."""
        try:
            # active_talk_interval is in minutes. 0 = Disabled.
            minutes = int(settings.get('active_talk_interval', 0))
            if minutes > 0:
                self.idle_threshold = minutes * 60
                logger.info(f"Active Talk Interval set to {minutes} min ({self.idle_threshold} sec).")
                self.idle_threshold = 0
                logger.info("Active Talk Disabled.")
            
            # --- Context Manager Init ---
            from src.services.core.context_manager import ContextManager
            self.context_manager = ContextManager()
            # Hook logging
            self.context_manager.set_log_callback(lambda msg, type='sys': self._send_log(msg, "info", type))
            # Hook message callback for Greetings
            if self.on_message_callback:
                self.context_manager.set_message_callback(self.on_message_callback)

            
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
            
            # Fallback to Environment Variable
            if not api_key:
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if api_key:
                    logger.info("ActiveEngine: API Key found in Environment Variables.")

            if api_key:
                vision_service.configure(api_key)
                logger.info("ActiveEngine: VisionService Configured with API Key.")
            else:
                logger.warning("ActiveEngine: No API Key found for VisionService (Config or Env). Vision features may fail.")
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

    def start_listening_loop(self):
        """Start continuous listening thread."""
        if not self.ears:
            logger.warning("ActiveEngine: No Ears configured.")
            return

        if self.hearing_active: return

        self.hearing_active = True
        logger.info("ActiveEngine: Starting Continuous Listening Loop...")
        threading.Thread(target=self._run_listening_loop, daemon=True).start()

    def stop_listening_loop(self):
        self.hearing_active = False
        logger.info("ActiveEngine: Stopping Continuous Listening Loop.")
        # self._stop_listening_loop() # Not implemented as method, just flag control

    def toggle_listening(self):
        """
        Toggles continuous listening mode.
        """
        # 1. Force OFF if ears missing (UI stuck fix)
        if not self.ears:
            if self.hearing_active:
                self.hearing_active = False
                logger.info("ActiveEngine: Continuous Listening FORCE STOP (No Ears).")
                return {"status": "success", "state": "off", "message": "Forced OFF (No Ears)"}
            else:
                logger.warning("ActiveEngine: No Ears configured. Cannot start listening.")
                return {"status": "error", "message": "No Ears configured"}

        # 2. Normal Toggle
        if self.hearing_active:
            # STOP
            self.stop_listening_loop()
            return {"status": "success", "state": "off"}
        else:
            # START
            self.start_listening_loop()
            return {"status": "success", "state": "on"}

    def set_ears(self, ears_instance):
        self.ears = ears_instance

    def _run_listening_loop(self):
        """Loop for continuous voice input."""
        logger.info("👂 [Active] Listening Loop Started.")
        no_speech_count = 0
        
        while self.hearing_active:
            if not self.ears: break
            
            try:
                # Listen with short timeout to allow loop check
                # listen_and_process blocks until speech or timeout
                res = self.ears.listen_and_process(timeout=1.0)
                
                if res and res.get('text'):
                    text = res['text']
                    emotion = res.get('emotion', 'neutral')
                    logger.info(f"🎤 [Active] Heard: {text} ({emotion})")
                    
                    # Log to UI
                    self._send_log(f"🎤 Heard: {text}", "info", "sys")

                    # Trigger Callback (Main API should handle this)
                    # We send a special payload type 'voice_input'
                    if self.on_message_callback:
                        import json
                        payload = {
                            "type": "voice_input",
                            "text": text,
                            "emotion": emotion
                        }
                        self.on_message_callback(json.dumps(payload, ensure_ascii=False))
                
            except Exception as e:
                logger.error(f"Listening Loop Error: {e}")
                time.sleep(1) # Backoff
        
        logger.info("👂 [Active] Listening Loop Stopped.")

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
            
            # 0. Context Update
            if hasattr(self, 'context_manager'):
                self.context_manager.update()

            # 1. Proactive Vision Loop
            if self.proactive_mode:
                # Determine current interval preference
                current_interval = self.vision_interval
                
                # Check active game engine override
                if hasattr(self, 'context_manager'):
                    active_engine = self.context_manager.get_active_engine()
                    # If active engine has 'settings' with 'vision_interval', use it
                    if active_engine and hasattr(active_engine, 'settings'):
                        # Override to 45s (or specific setting) for AoE2
                        # Default AoE2DB config is 60s, user asked for 45s override logic.
                        # Let's verify valid interval:
                        override = active_engine.settings.get('vision_interval', 45)
                        current_interval = override
                        # logger.debug(f"ActiveEngine: Interval overridden to {current_interval}s by Context.")

                if time.time() - self.last_vision_time > current_interval:
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
            if self.on_message_callback and not self.stealth_mode:
                import json
                # Send expression trigger (requires Main.py support)
                self.on_message_callback(json.dumps({"type": "expression", "name": "focused"}))

            # 1. Capture
            try:
                from src.services.vision.window_target_manager import window_target_manager
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

            # 2. Vision Analysis (Routing)
            active_game_engine = None
            if hasattr(self, 'context_manager'):
                active_game_engine = self.context_manager.get_active_engine()

            if active_game_engine:
                 # === Game Logic Route ===
                 self._send_log(f"🎮 [Active] Using Game Engine: {type(active_game_engine).__name__}", "info", "sys")
                 
                 # Analyze (Assuming Engine has standardized method or we cast)
                 # For AoE2, we know it has analyze_situation & generate_commentary_prompt
                 # We need to feed it text? No, AoE2 engine planned to take JSON from Vision?
                 # Wait, VisionService returns TEXT description by default.
                 # Actually AoE2 Prompt Logic expected "Vision JSON".
                 # BUT VisionService.analyze_image returns STRING (Gemini caption).
                 # We need a Structured Analysis for Games?
                 # Or we ask Gemini to output JSON for AoE2?
                 
                 # Update: Let's ask VisionService to analyze with specific prompt for the game
                 game_prompt = "Identify unit composition, resources, and score. Return JSON." 
                 # Currently analyze_image takes 'prompt'.
                 
                 vision_text = vision_service.analyze_image(image, prompt="Analyze the Age of Empires 2 game screen. List user civilization, score, expected age, and visible enemy units/colors in JSON format.")
                 
                 # Now feed text to Engine
                 # Note: commentary_engine.analyze_situation expects JSON string or dict.
                 # But vision_text from current vision_service is usually TEXT description.
                 # We must ensure Vision Service returns JSON if we asked for it. 
                 # However, 'vision_service.analyze_image' returns 'text' (Gemini output).
                 
                 # The prompt we sent: "Analyze... Return JSON format."
                 # So we should attempt to extract JSON from 'vision_text'
                 
                 import json
                 import re
                 
                 json_data = {}
                 try:
                     # Simple extraction: find first '{' and last '}'
                     match = re.search(r'\{.*\}', vision_text, re.DOTALL)
                     if match:
                         json_str = match.group(0)
                         json_data = json.loads(json_str)
                     else:
                         # Fallback: maybe it IS just text?
                         logger.warning("ActiveEngine: Could not extract JSON from Vision response. Using raw text.")
                         # If we pass raw text, analyze_situation might fail.
                         # Let's try to construct dummy JSON or fail gracefully.
                         json_data = {"error": "JSON parse failed", "raw_text": vision_text}
                 except Exception as e:
                     logger.error(f"ActiveEngine: JSON Parse Error: {e}")
                     json_data = {"error": str(e)}

                 analysis = active_game_engine.analyze_situation(json_data)
                 
                 # Generate System Prompt
                 sys_prompt = active_game_engine.generate_commentary_prompt(analysis)
                 
                 if sys_prompt:
                     self._send_log(f"🧠 [AoE2] Prompt Generated. Requesting Speech...", "info", "mind")
                     
                     # Generate Speech using AIEngine with this system prompt
                     # generate_proactive_message(context) uses the context as instruction.
                     result = self.ai_engine.generate_proactive_message(context=sys_prompt)
                     
                     # Force decision to SPEAK
                     text_content = result.get('text', '')
                     if not text_content: text_content = "戦況分析完了。" # Fallback
                     
                     decision = {
                         "action": "speak", 
                         "text": text_content, 
                         "topic_tag": "game_strategy",
                         "emotion": result.get('emotion', 'neutral'),
                         "suggestions": result.get('suggestions', ["なるほど", "ありがとう"])
                     }
                 else:
                     logger.warning("Game Engine returned no prompt (Parsing failed?)")
                     decision = {"action": "silent"}

            else:
                # === Standard Logic Route ===
                context_title = window_target_manager.target_title if window_target_manager.target_hwnd else "Full Screen Desktop"
                vision_text = vision_service.analyze_image(image, prompt=f"User's active window: '{context_title}'.")
                
                logger.info(f"👁️ [Vision] Saw: {vision_text}")
                self._send_log(f"Saw: {vision_text}", "info", "vision")
    
                # 3. Decision Making (via ProactiveChatManager)
                from src.services.core.proactive_chat_manager import ProactiveChatManager
                manager = ProactiveChatManager()
                if not manager.client and vision_service.api_key:
                    manager.configure(vision_service.api_key)
                
                decision = manager.decide_next_action(vision_text)
            
            # --- Common Execution Logic ---
            action = decision.get("action", "silent").lower()
            
            action = decision.get("action", "silent").lower()
            speak_text = decision.get("text", "").strip()
            topic_tag = decision.get("topic_tag", "unknown")
            emotion = "neutral" # Default, maybe extract from decision if added? ProactiveChatManager returns JSON.
            # Update prompt in manager to return emotion if needed, or infer.
            
            # Logging
            logger.info(f"🧠 [Proactive] Decision: {action.upper()} | Topic: {topic_tag} | Text: {speak_text[:30]}...")

            if action == "speak" and speak_text:
                # Check Silent Mode (Global Setting) or Stealth Mode
                if self.proactive_silent_mode or self.stealth_mode:
                    logger.info("🤫 [Proactive] Silent Mode / Stealth Mode: Skipping TTS, Log only.")
                    self._send_log(f"(Stealth) {speak_text}", "info", "mind")
                    # Send pure text for controller to log when in stealth
                    if self.stealth_mode and self.on_message_callback:
                        import json
                        self.on_message_callback(json.dumps({"type": "stealth_log", "text": speak_text}))
                else:
                    # Construct Payload for Frontend
                    # Reuse Suggestion Padding Logic (could be refactored to helper but keeping inline for now)
                    
                    # --- Suggestion Padding Logic (Adapter) ---
                    # Because decision doesn't return suggestions, we generate generic ones or use simplified list.
                    # Or ask SuggestionEngine.
                    final_10 = ["もっと詳しく教えて", "ありがとう", "他の話題について"]
                    
                    try:
                        from src.services.content.suggestion_engine import SuggestionEngine
                        eng = SuggestionEngine(self.ai_engine)
                        hist = f"Vision Context: {vision_text}\nAI Spoke: {speak_text}"
                        more = eng.generate(hist, "Unknown", "あなた")
                        final_10.extend([m for m in more if m not in final_10])
                    except:
                        pass
                        
                    # Love Slot
                    from src.services.content.affection_manager import AffectionManager
                    if not any(AffectionManager.is_affectionate(s) for s in final_10):
                         love = f"❤ {AffectionManager().get_random_affection()}"
                         final_10.append(love)
                         
                    final_10 = final_10[:10]

                    payload = {
                        "text": speak_text,
                        "emotion": emotion, # You might want to ask Manager for emotion too
                        "suggestions": final_10,
                        "type": "proactive"
                    }
                    if self.on_message_callback:
                        import json
                        self.on_message_callback(json.dumps(payload, ensure_ascii=False))

            elif action == "motion":
                # Handle Motion only
                # self.on_message_callback(json.dumps({"type": "motion", "id": decision.get("motion_id")}))
                pass

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
                    from src.services.content.suggestion_engine import SuggestionEngine
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
            from src.services.content.affection_manager import AffectionManager
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
