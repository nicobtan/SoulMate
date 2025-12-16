import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class BubbleService:
    def __init__(self, services_container=None):
        self.services = services_container
        self._active_bubbles = {} # Map action_id -> bubble_packet
        # History for de-duplication (Keep last 10)
        self._history = [] 
        logger.info("BubbleService Initialized (Date-Aware Mode)")

    def _get_max_balloons(self):
        default_max = 3
        if self.services and hasattr(self.services, 'config_manager'):
            return self.services.config_manager.get('max_balloons', default_max)
        return default_max

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
            "now": now,
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
        Generate a smart context-aware bubble payload.
        """
        ctx = self._get_time_context()
        slot = ctx["slot"]
        weekday = ctx["weekday"]
        
        logger.info(f"Generating bubble for: {ctx['formatted']}, Slot: {slot}")

        # 0. Check Limits
        max_b = self._get_max_balloons()
        current_count = len(self._active_bubbles)
        if current_count >= max_b:
            logger.info(f"Bubble Limit Reached ({current_count}/{max_b}). Skipping generation.")
            return None

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

        # 3. Personalization
        user_topics = self._get_personalized_topics()
        dynamic_topics = []
        # 3. Personalization & Discovery
        # Discovery Mode: 30% chance to pick something random/new
        is_discovery = False
        discovery_topics = ["宇宙の謎", "深海生物", "古代文明", "最新ガジェット", "珍しい動物", "世界の絶景", "心理学トリビア"]
        
        user_topics = self._get_personalized_topics()
        dynamic_topics = []
        
        # Decide Discovery vs Interest
        if random.random() < 0.3:
            is_discovery = True
            t = random.choice(discovery_topics)
            dynamic_topics = [
                f"知ってた？{t}の話",
                f"{t}について調べてみた",
                f"{t}って面白いよ！"
            ]
        elif user_topics:
            t = random.choice(user_topics)
            dynamic_topics = [
                f"最新の{t}事情",
                f"{t}について",
                f"{t}のニュースある？"
            ]

        # 4. Selection Process
        # Decide Strategy: Special > Dynamic > Slot
        strategy_roll = random.random()
        
        selected_cat = "topics"
        selected_text = "何か話そう？"

        if special_messages and strategy_roll < 0.4:
            # 40% chance for special day message if available
            msg = random.choice(special_messages)
            selected_cat = msg["cat"]
            selected_text = msg["text"]
        
        elif dynamic_topics and strategy_roll < 0.7:
             # 30% chance (0.4 to 0.7) for personalized topic
             selected_cat = "topics"
             selected_text = random.choice(dynamic_topics)
             
        else:
             # Fallback to standard time slot messages
             slot_data = candidates.get(slot, candidates["daytime"])
             available_cats = list(slot_data.keys())
             selected_cat = random.choice(available_cats)
             selected_text = random.choice(slot_data[selected_cat])

        action_id = f"BUBBLE_{weekday.upper()}_{slot.upper()}_{random.randint(1000,9999)}"
        
        packet = {
            "category": selected_cat,
            "text": selected_text,
            "action_id": action_id,
            "metadata": ctx,
            "type": "discovery" if is_discovery else "normal"
        }
        
        # De-duplication Check
        if selected_text in self._history:
            logger.info(f"Duplicate bubble text '{selected_text}'. Skipping.")
            return None
            
        self._history.append(selected_text)
        if len(self._history) > 20: self._history.pop(0)
        
        self._active_bubbles[action_id] = packet
        return packet

    def remove_bubble(self, action_id):
        """Removes a bubble and triggers refill if needed."""
        if action_id in self._active_bubbles:
            del self._active_bubbles[action_id]
            logger.info(f"Removed bubble: {action_id}")
            return True
        return False
        
    def refill_bubbles(self):
        """Attempts to generate new bubbles until max is reached or failure."""
        max_b = self._get_max_balloons()
        current = len(self._active_bubbles)
        if current < max_b:
            # Generate one
            return self.get_smart_bubble()
        return None
        
        self._active_bubbles[action_id] = packet
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
- Be friendly and engaging.
- If it's a question, wait for user answer.
- If it's a topic, start with the latest info you found.
"""
             
             # Run in thread
             import threading
             def run_talk():
                 try:
                     response_text = api._ai_engine.generate_response(prompt)
                     
                     # Simple logic to extract string if dict
                     msg = response_text
                     if isinstance(response_text, dict):
                         # If engine usually returns a dict structure, handle it?
                         # Assuming default engine returns dict or str based on previous logs
                         # We'll just dump it as is for the frontend handler
                         import json
                         api.push_message_callback(json.dumps(response_text, ensure_ascii=False))
                     else:
                         import json
                         payload = {"response": str(msg), "emotion": "happy"}
                         api.push_message_callback(json.dumps(payload, ensure_ascii=False))
                         
                 except Exception as e:
                     logger.error(f"Bubble Talk Failed: {e}")

             threading.Thread(target=run_talk, daemon=True).start()

        return {"status": "ok", "action": action_id}
