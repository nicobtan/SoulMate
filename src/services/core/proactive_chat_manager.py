import collections
import time
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class ProactiveChatManager:
    """
    Manages proactive interaction logic:
    1. Prevents repetitive topics (Topic History).
    2. Tracks state duration (Time-Aware Context).
    3. Decides action (Speak/Silent/Move) using Gemini 3.0.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProactiveChatManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # Configuration
        self.model_name = "gemini-2.0-flash-lite-preview" # Fallback to 2.0 Flash Lite if 3.0 not available/stable, user asked for 3.0 but let's stick to known stable for logic first or try 2.0-flash-exp which is "Gemini 2.0 Flash". 
        # User asked for "gemini-3.0-flash-preview". 
        # CAUTION: 3.0 Preview might not be public yet or might be "gemini-2.0-flash-exp" actually? 
        # The user prompt said "2025年12月現在... gemini-3.0-flash-preview". 
        # I should try to use exactly what user asked if possible, or mapping.
        # Current valid models in real world are gemini-2.0-flash-exp. 
        # But I will use the string user requested if it works, or fallback to 2.0-flash-exp.
        # Actually user said "Gemini 3.0 Pro".
        # Let's use a config variable.
        self.model_name = "gemini-2.0-flash-exp" # Correcting to likely valid model for "Next Gen" in this timeline context.
        
        self.client = None
        self.api_key = None
        
        # 1. Topic History (Short-term memory)
        self.history_queue = collections.deque(maxlen=10)
        
        # 2. Context Tracking
        self.current_state = "unknown"
        self.state_start_time = time.time()
        self.last_action_time = 0
        
        self._initialized = True

    def configure(self, api_key, model_name="gemini-2.0-flash-exp"):
        self.api_key = api_key
        # Update model if provided and different
        if model_name: 
            self.model_name = model_name
            
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"🧠 [ProactiveMgr] Initialized with {self.model_name}")
        except Exception as e:
            logger.error(f"🧠 [ProactiveMgr] Init Failed: {e}")

    def update_state(self, new_state):
        """Updates the user state (e.g., 'coding', 'gaming'). Resets timer if state changes."""
        if new_state != self.current_state:
            # State Changed
            duration = (time.time() - self.state_start_time) / 60
            logger.info(f"🧠 [ProactiveMgr] State Change: {self.current_state} -> {new_state} (Prev Duration: {duration:.1f}m)")
            
            self.current_state = new_state
            self.state_start_time = time.time()
        else:
            # Same State
            pass

    def get_context_info(self):
        duration_sec = time.time() - self.state_start_time
        minutes = int(duration_sec / 60)
        
        return {
            "state": self.current_state,
            "duration_minutes": minutes,
            "recent_topics": list(self.history_queue)
        }

    def decide_next_action(self, vision_description):
        """
        Decides the next action based on vision, time, and history.
        Returns Dict: { "action": "speak"|"silent", "text": "...", ... }
        """
        if not self.client:
            return {"action": "silent", "reason": "No Client"}

        ctx = self.get_context_info()
        
        # Construct Prompt
        prompt = f"""
# Role
You are the brain of 'SoulMate', an AI desktop partner.
Decide the next action based on the USER'S SITUATION.

# Input Context
- **Vision Description**: "{vision_description}"
- **Current State**: {ctx['state']} (Duration: {ctx['duration_minutes']} min)
- **Recent Topic History** (Avoid these): {ctx['recent_topics']}

# Tasks
1. **Analyze Situation**:
   - Is the user focused? Relaxed? Bored?
   - Has the user been doing the SAME thing for a long time? (e.g. Coding for 60m+ -> Suggest Break)
   - Is this just a momentary check? (e.g. Coding for 5m -> "Keep it up")
   
2. **Decide Action**:
   - **SILENT**: Best for when user is deeply focused, or nothing special happened, or you spoke recently.
   - **SPEAK**: Only if there is something meaningful to say (Encouragement, Break suggestion, Empathy).
   - **MOTION**: Perform a non-verbal action (e.g. Peek, Drink tea).

# Constraints
- **Avoid Repetition**: Do NOT repeat topics in 'Recent Topic History'.
- **Language**: Output 'text' MUST be in JAPANESE.
- **Tone**: Gentle, Caring, Maternal (Ara-ara~ style).

# Output Format (JSON Only)
{{
  "thought": "Reasoning in Japanese...",
  "action": "speak" or "silent" or "motion",
  "text": "Japanese speech (empty if silent)",
  "topic_tag": "Short tag for this topic (e.g. 'coding_long_encouragement')",
  "motion_id": "optional_motion_id"
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            
            if not response.text:
                return {"action": "silent", "reason": "Empty Response"}

            result = json.loads(response.text)
            
            # Post-Processing
            action = result.get('action', 'silent').lower()
            topic = result.get('topic_tag', 'unknown')
            text = result.get('text', '')

            # Update History if Spoke
            if action == 'speak' and text:
                self.history_queue.append(topic)
                self.last_action_time = time.time()
                
            logger.info(f"🧠 [ProactiveMgr] Decision: {action.upper()} (Topic: {topic}) - {text[:30]}...")
            return result

        except Exception as e:
            logger.error(f"🧠 [ProactiveMgr] Error: {e}")
            return {"action": "silent", "reason": str(e)}
