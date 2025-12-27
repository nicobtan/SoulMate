import logging
import random
import json
from datetime import datetime

logger = logging.getLogger(__name__)

import time

class BubbleService:
    def _infer_category(self, text: str) -> str:
        """Infer category based on keywords in text."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["宇宙", "星", "スペース", "深海"]): return "space"
        if any(w in text_lower for w in ["ガジェット", "スマホ", "pc", "技術", "ai", "tech"]): return "tech"
        if any(w in text_lower for w in ["動物", "アニマル", "ペット", "猫", "犬"]): return "fun"
        if any(w in text_lower for w in ["ゲーム", "game", "遊び"]): return "game"
        if any(w in text_lower for w in ["ニュース", "news", "情勢"]): return "news"
        if any(w in text_lower for w in ["健康", "運動", "サプリ", "睡眠"]): return "health"
        if any(w in text_lower for w in ["映画", "ドラマ", "アニメ"]): return "movie"
        if any(w in text_lower for w in ["音楽", "ライブ", "フェス"]): return "music"
        if any(w in text_lower for w in ["絶景", "旅行", "温泉"]): return "travel"
        return "topics"

    def __init__(self, services_container=None):
        self.services = services_container
        self._active_bubbles = {} # Map action_id -> bubble_packet
        self._history = [] 
        self._last_gen_time = 0
        self._max_balloons_cache = 3
        # Allow immediate generation on startup
        self._startup_mode = True 
        logger.info("BubbleService Initialized (Stability Fixed)")

    def update_settings(self, config: dict):
        """Called when server settings are updated."""
        if 'max_balloons' in config:
            new_max = int(config['max_balloons'])
            if new_max != self._max_balloons_cache:
                self._max_balloons_cache = new_max
                logger.info(f"Bubble Limit Updated: {self._max_balloons_cache}")
                # Trigger refill if limit increased
                self.refill_bubbles()

    def _get_max_balloons(self):
        # Use cached value for consistency, update via update_settings
        # Fallback to config reading if needed
        if self.services and hasattr(self.services, 'config_manager'):
             self._max_balloons_cache = int(self.services.config_manager.get('max_balloons', self._max_balloons_cache))
        return self._max_balloons_cache

    def _get_time_context(self):
        """
        Get detailed time context including day of week and season.
        """
        now = datetime.now()
        hour = now.hour
        weekday = now.strftime("%A") # Monday, Tuesday...
        month = now.month
        
        # Time Slot
        if 5 <= hour < 10: slot = "morning"
        elif 10 <= hour < 14: slot = "daytime"
        elif 14 <= hour < 17: slot = "teatime"
        elif 17 <= hour < 20: slot = "evening"
        elif 20 <= hour < 24: slot = "night"
        else: slot = "midnight"
        
        # Season
        if month in [3, 4, 5]: season = "spring"
        elif month in [6, 7, 8]: season = "summer"
        elif month in [9, 10, 11]: season = "autumn"
        else: season = "winter"
        
        return {
            "now": now.isoformat(), # Fixed: Convert to string for JSON serialization
            "slot": slot,
            "weekday": weekday,
            "season": season,
            "formatted": now.strftime("%Y-%m-%d (%A) %H:%M")
        }

    def _get_personalized_topics(self):
        """
        Extract topics from UserManager if available.
        """
        topics = []
        if self.services and hasattr(self.services, 'user_manager'):
            profile = self.services.user_manager.profile_data
            if not profile:
                return []
            
            # Extract varied interests
            if 'likes' in profile: topics.extend(profile['likes'])
            if 'games' in profile: topics.extend(profile['games'])
            if 'tech_stack' in profile: topics.extend(profile['tech_stack'])
            
        return list(set(topics)) # Dedup

    def get_smart_bubble(self):
        """
        Generate a single smart context-aware bubble payload.
        Does NOT check limits/time internally (logic moved to refill_bubbles).
        """
        ctx = self._get_time_context()
        slot = ctx["slot"]
        weekday = ctx["weekday"]
        
        
        # 1. Base Candidates (Time Slot)
        candidates = {
            "morning": {
                "bond": ["おはよう！", "よく眠れた？", "今日の予定を確認しよう"],
                "utility": ["ゴミ出しは大丈夫？", "今日も一日頑張ろう"],
            },
            "daytime": {
                "bond": ["お昼は何にする？", "調子はどう？"],
                "utility": ["進捗どうですか？", "適度に休憩してね"],
            },
            "teatime": {
                "play": ["一息入れない？", "おやつタイムだよ", "コーヒーでもどう？"],
                "topics": ["ちょっと雑談しない？"],
            },
            "evening": {
                "bond": ["お疲れ様！", "もうすぐ定時？", "夕飯決めた？"],
                "play": ["今日のニュース見る？"],
            },
            "night": {
                "bond": ["リラックスタイムだね", "お風呂入った？"],
                "play": ["ゲームでもする？"],
            },
            "midnight": {
                "bond": ["まだ起きてるの？", "無理しないでね", "そろそろ寝ようか"],
                "utility": ["夜更かしは美容に悪いよ"],
            }
        }
        
        # 2. Add Special Day Logic (Weekday/Weekend)
        special_messages = []
        
        # Monday Morning
        if weekday == "Monday" and slot == "morning":
            special_messages.append({"cat": "bond", "text": "また一週間始まるね！無理せずいこう"})
        
        # Friday Night
        if weekday == "Friday" and slot in ["evening", "night"]:
            special_messages.append({"cat": "play", "text": "華金だね！今夜は楽しもう！"})
            special_messages.append({"cat": "bond", "text": "一週間お疲れ様！"})

        # Weekend
        if weekday in ["Saturday", "Sunday"]:
             if slot == "morning":
                 special_messages.append({"cat": "bond", "text": "休日は何する予定？"})
             elif slot == "daytime":
                 special_messages.append({"cat": "play", "text": "どこか出かける？"})
             elif slot == "night":
                 special_messages.append({"cat": "play", "text": "明日のためにゆっくり休んでね"})

        # 3. Personalization & Discovery
        is_discovery = False
        
        # dynamic_topics generation using TopicSelector
        dynamic_topics = []
        
        if self.services and hasattr(self.services, 'topic_selector') and hasattr(self.services, 'interest_manager'):
            # Load candidates
            topic_candidates = self.services.interest_manager.load_topics()
            # Decide
            selection = self.services.topic_selector.decide_topic(topic_candidates)
            topic = selection['topic']
            source = selection['source']
            
            if source == 'chaos':
                is_discovery = True
                dynamic_topics = [
                    f"「{topic}」について",
                    f"💡 {topic}の話",
                    f"知ってる？ {topic}"
                ]
            else:
                 dynamic_topics = [
                    f"「{topic}」の話",
                    f"{topic}のニュース",
                    f"{topic}について"
                ]
        else:
            # Fallback if no selector
            fallback_topics = ["宇宙の謎", "深海生物", "古代文明"]
            t = random.choice(fallback_topics)
            dynamic_topics = [f"「{t}」について"]

        # 4. Selection Process
        strategy_roll = random.random()
        
        selected_cat = "topics"
        selected_text = "何か話そう？"

        if special_messages and strategy_roll < 0.4:
            msg = random.choice(special_messages)
            selected_cat = msg["cat"]
            selected_text = msg["text"]
        elif dynamic_topics and strategy_roll < 0.7:
             selected_text = random.choice(dynamic_topics)
             selected_cat = self._infer_category(selected_text)
        else:
             slot_data = candidates.get(slot, candidates["daytime"])
             available_cats = list(slot_data.keys())
             selected_cat = random.choice(available_cats)
             selected_cat = random.choice(available_cats)
             selected_text = random.choice(slot_data[selected_cat])

        # 4.5 Love Bubble Injection (Priority: Guarantee > Random)
        # Ensure at least one heart is always floating.
        has_love = any(b.get('category') == 'love' for b in self._active_bubbles.values())
        
        force_love = False
        if not has_love:
             force_love = True # Guarantee: No heart exists, so we make one.
        elif not special_messages and random.random() < 0.2:
             force_love = True # Random Mix: 20% chance even if one exists

        if force_love:
             from .affection_manager import AffectionManager
             selected_text = AffectionManager().get_random_affection()
             selected_cat = "love"

        # De-duplication Check
        if selected_text in self._history:
            return None # Retry caller
            
        self._history.append(selected_text)
        if len(self._history) > 20: self._history.pop(0)
        
        action_id = f"BUBBLE_{weekday.upper()}_{slot.upper()}_{random.randint(1000,9999)}"
        
        packet = {
            "category": selected_cat,
            "text": selected_text,
            "action_id": action_id,
            "metadata": ctx,
            "type": "discovery" if is_discovery else "normal"
        }
        
        self._active_bubbles[action_id] = packet
        logger.info(f"[System] Bubble Injected: {selected_text} ({packet['type']})")
        return packet

    def remove_bubble(self, action_id):
        """Removes a bubble and triggers refill if needed."""
        if action_id in self._active_bubbles:
            del self._active_bubbles[action_id]
            logger.info(f"Removed bubble: {action_id} | Remaining: {len(self._active_bubbles)}")
            return True
        logger.warning(f"Attempted to remove non-existent bubble: {action_id}")
        return False
        
    def refill_bubbles(self):
        """
        Smart Refill Logic:
        1. Checks time interval (5 min) unless it's startup or empty.
        2. Loops until MAX is reached.
        """
        max_b = self._get_max_balloons()
        current = len(self._active_bubbles)
        now = time.time()

        # Guard Logic: If full, return immediately (silent)
        if current >= max_b:
            return None 
        
        # User Request: "Immediate 5 on startup"
        # If count is 0, we imply urgency/startup.
        is_urgent = (current == 0) or self._startup_mode
        
        # Interval Check (300s = 5min)
        if not is_urgent and (now - self._last_gen_time < 300):
            return None # Too soon
            
        logger.info(f"Refilling Bubbles... (Current: {current}, Max: {max_b}, Urgent: {is_urgent})")
        
        # User Request: "3 bubbles on startup"
        target_fill = max_b
        if self._startup_mode:
            target_fill = min(max_b, 3)

        new_bubbles = []
        attempts = 0
        while len(self._active_bubbles) < target_fill and attempts < 10:
            attempts += 1
            bubble = self.get_smart_bubble()
            if bubble:
                new_bubbles.append(bubble)
        
        if new_bubbles:
            self._last_gen_time = now
            self._startup_mode = False # Startup burst done
            
        return new_bubbles

    def register_manual_bubble(self, category, text):
        """
        Manually register a bubble from frontend (e.g. Topic Button).
        Returns the bubble packet including a valid Action ID.
        """
        ctx = self._get_time_context()
        # Generate ID
        action_id = f"MANUAL_{ctx['weekday'].upper()}_{random.randint(10000,99999)}"
        
        packet = {
            "category": category,
            "text": text,
            "action_id": action_id,
            "metadata": ctx,
            "type": "manual"
        }
        
        # Store in active list so handle_action can find it
        self._active_bubbles[action_id] = packet
        logger.info(f"[System] Manual Bubble Registered: {text} ({action_id})")
        return packet

    # Wrapper for backward compatibility
    def get_test_bubble(self):
        return self.get_smart_bubble()

    def handle_action(self, action_id: str):
        """
        Handle the action triggered by the bubble with Date/Time Grounding.
        """
        logger.info(f"Handling Bubble Action: {action_id}")
        
        packet = self._active_bubbles.get(action_id)
        if not packet:
            logger.warning(f"Bubble context lost for {action_id}")
            return {"status": "error", "message": "Context lost"}

        text_content = packet.get('text', '')
        cat = packet.get('category', '')
        
        # Get Fresh Time Context
        time_ctx = self._get_time_context()
        time_str = time_ctx['formatted'] # e.g. "2025-12-16 (Tuesday) 19:30"
        
        # Trigger Active Talk via API
        api = self.services
        if api and hasattr(api, '_ai_engine'):
             
             # Grounding Instruction Construction
             grounding_instruction = ""
             if cat == "topics" or "ニュース" in text_content or "事情" in text_content:
                 grounding_instruction = """
IMPORTANT: The user is interested in this topic.
**USE GOOGLE SEARCH TOOL** to find the LATEST information about it.
- **PROVIDE URLs**: You MUST include the link to the news/video you found.
- If you cannot find a specific URL, do NOT invent one. Instead, talk generally.
- Verifiable facts are preferred over general statements.
"""

             prompt = f"""
[System Notification]
User clicked a bubble: "{text_content}" (Category: {cat}).
[Current Time] {time_str}

[Instruction]
The user accepted your proposal to talk about "{text_content}".
Reply to the user naturally to start this conversation.
Consider the current time (Morning/Night/Weekday/Weekend) in your tone.
{grounding_instruction}

[Output Requirement]
Response Format: **TOON (Token-Oriented Object Notation)**
- Use your Persona's tone.
- Friendly and engaging.
- If it's a question, wait for user answer.
- Provide EXACTLY 5 suggestions (4 specific follow-ups + "他の話題について").

response:
  text: Your friendly response here...
emotion: happy
suggestions:
  - Option 1
  - Option 2
  - Option 3
  - Option 4
  - 他の話題について
"""
             
             # Run in thread
             import threading
             def run_talk():
                 from src.services.ai_engine import logger as ai_logger # Use logger
                 try:
                     logger.info(f"Bubble Trigger: Generating response for: {text_content}")
                     response_payload = api._ai_engine.generate_response(prompt)
                     
                     # 1. Normalize Payload
                     final_payload = {}
                     
                     if isinstance(response_payload, dict):
                         # It's already valid JSON-like dict from AIEngine (RAG enabled)
                         final_payload = response_payload
                         # Validation
                         if "response" not in final_payload and "text" in final_payload:
                             final_payload["response"] = final_payload["text"]
                     else:
                         # String fallback (Legacy or Error String)
                         import json
                         import re
                         try:
                             # Clean code blocks
                             clean_text = re.sub(r'```json\s*', '', str(response_payload))
                             clean_text = re.sub(r'```', '', clean_text)
                             final_payload = json.loads(clean_text)
                         except:
                             # Plain text fallback
                             final_payload = {"response": str(response_payload), "emotion": "happy"}

                     # 2. Add Grounding Info if missing (Safety)
                     if "grounding_info" not in final_payload:
                         final_payload["grounding_info"] = None
                     
                     # --- Suggestion Padding Logic (Ensure 10 items) ---
                     # Same logic as ChatApi
                     suggestions = final_payload.get("suggestions", [])
                     
                     # 1. Fixed Nav
                     fixed = ["もっと詳しく教えて", "他の話題について"]
                     
                     # 2. Dynamic (Target 8)
                     dynamic = [s for s in suggestions if s not in fixed] # Filter existing fixed
                     
                     if len(dynamic) < 8:
                         # Attempt to use SuggestionEngine Integration
                         try:
                             from src.services.suggestion_engine import SuggestionEngine
                             engine = SuggestionEngine(api._ai_engine) # Helper instance
                             
                             # Simple Context for Bubble
                             # We use the prompt's context implicitly
                             # Need to extract user name?
                             user_name = "あなた"
                             if hasattr(api, 'user_manager') and hasattr(api.user_manager, 'user_config'):
                                 user_name = api.user_manager.user_config.get('name', 'あなた')
                                 
                             history_txt = f"Bubble Topic: {text_content}\nAI Response: {final_payload.get('response', '')}"
                             profile_txt = "Unknown"
                             if hasattr(api, 'user_manager'): profile_txt = api.user_manager.get_profile_context()

                             more_sug = engine.generate(history_txt, profile_txt, user_name)
                             for ms in more_sug:
                                 if ms not in dynamic and len(dynamic) < 8:
                                     dynamic.append(ms)
                         except Exception as e:
                             logger.warning(f"Bubble Suggestion Padding Failed: {e}")
                             
                     # Fallback Padding
                     while len(dynamic) < 8:
                         dynamic.append("...その他")
                         
                     # Combine: Fixed(2) + Dynamic(8) = 10
                     final_10 = fixed + dynamic[:8]
                     
                     # Love Slot Logic
                     from src.services.affection_manager import AffectionManager
                     if not any(AffectionManager.is_affectionate(s) for s in final_10):
                         love = f"❤ {AffectionManager().get_random_affection()}"
                         if len(final_10) >= 10: final_10[-1] = love
                         else: final_10.append(love)
                         
                     final_payload["suggestions"] = final_10
                     # --------------------------------------------------

                     # 3. Push to UI
                     import json
                     # We use json.dumps to ensure it's a string for the callback, 
                     # but main.py's push_message_callback expects a JSON string or raw string.
                     api.push_message_callback(json.dumps(final_payload, ensure_ascii=False))

                 except Exception as e:
                     logger.error(f"Bubble Talk Failed: {e}", exc_info=True)
                     # Fallback Message to UI so it doesn't hang
                     error_payload = {"response": "ごめんなさい、ちょっと考えがまとまらなかったわ。", "emotion": "sad"}
                     api.push_message_callback(json.dumps(error_payload, ensure_ascii=False))

             threading.Thread(target=run_talk, daemon=True).start()

        return {"status": "ok", "action": action_id}
