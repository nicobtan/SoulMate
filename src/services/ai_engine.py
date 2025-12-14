import google.generativeai as genai
import logging
import datetime
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.api_key = None
        self.model_name = "gemini-2.5-flash-lite"
        self.chat_session = None
        self.history = []
        self.system_instruction = "You are a helpful AI assistant."

    def configure(self, api_key, model_name="gemini-2.5-flash-lite", system_instruction=None, profile_data=None):
        """Configures the AI Engine with new settings."""
        self.api_key = api_key
        self.model_name = model_name
        
        # Priority: Profile Data > Explicit Instruction > Default
        if profile_data:
            self.system_instruction = self._construct_system_instruction(profile_data)
        elif system_instruction:
            self.system_instruction = system_instruction
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Reset chat session when config changes
                self.chat_session = None 
                logging.info(f"AIEngine configured with model: {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to configure Gemini API: {e}")

    def generate_response(self, message, context=None):
        """Generates a JSON response for the given message, or raw text if Action."""
        if not self.api_key:
            return "設定画面でGoogle Gemini APIキーを設定してください。"

        try:
            # Initialize Chat Session if needed
            if self.chat_session is None:
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction,
                    generation_config={"response_mime_type": "application/json"}
                )
                self.chat_session = model.start_chat(history=self.history)

            # Construct Message with Context
            now_jst = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            base_context = f"Current Time: {now_jst}\n"
            
            if context:
                base_context += f"{context}\n"
            
            full_message = f"""
[Context/Memory]
{base_context}

[User Input]
{message}

[SYSTEM REMINDER]
JSON Output Required! 
Key "suggestions": Provide 2-3 short, natural Japanese response options for the USER to say next.
"""
            # Send Message
            response = self.chat_session.send_message(full_message)
            raw_text = response.text
            
            # --- Parsing Logic ---
            try:
                # 1. Try passing as JSON directly
                data = json.loads(raw_text)
                return data 
                # Expected: {'response': '...', 'emotion': '...', 'suggestions': [...]}
            except json.JSONDecodeError:
                # 2. Fallback: Check for Action Command or Plain Text
                # If it's an action command, it might not be JSON if the model ignored instructions
                # But we set response_mime_type=application/json, so it SHOULD be JSON.
                # However, if we need to support pure text Actions, we might need to be careful.
                # Let's assume the model is smart enough to put [ACTION] inside "response" key 
                # OR we accept that Action Commands might come as raw text if the model hallucinates.
                logging.warn(f"JSON Decode Failed. Raw: {raw_text}")
                return {"response": raw_text, "emotion": "neutral", "suggestions": []}

        except Exception as e:
            logging.error(f"Generation Error: {e}")
            return {"response": f"エラーが発生しました: {str(e)}", "emotion": "sad", "suggestions": []}

    def generate_proactive_message(self, context=None):
        """Generates a proactive message (Agent initiates topic)."""
        if not self.api_key:
            return {"response": "API Key not configured.", "emotion": "neutral", "suggestions": []}

        try:
            # Initialize Chat Session if needed
            if self.chat_session is None:
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction,
                    generation_config={"response_mime_type": "application/json"}
                )
                self.chat_session = model.start_chat(history=self.history)

            # Context
            now_jst = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            base_context = f"Current Time: {now_jst}\n"
            if context:
                base_context += f"{context}\n"

            # Hidden System Prompt as User Input
            full_message = f"""
[Context]
{base_context}

[SYSTEM INSTRUCTION]
ユーザーから「話しかけて」という合図がありました（もしくは沈黙が続いています）。
能動的かつ自然に、あなたから話しかけてください。
話題の例:
1. 現在の時刻や日付に関連すること
2. 季節、天気、またはランダムな雑談（食べ物、趣味など）
3. 夜なら「お疲れ様」や「眠くない？」など

**重要: 必ず設定されたキャラクターの口調（日本語）で話してください。**
出力は標準のJSONフォーマット必須です。
"""
            # Send (Simulation)
            response = self.chat_session.send_message(full_message)
            raw_text = response.text
             
            # Parsing (Duplicate logic for safety)
            try:
                data = json.loads(raw_text)
                return data 
            except json.JSONDecodeError:
                logging.warn(f"JSON Decode Failed (Proactive). Raw: {raw_text}")
                return {"response": raw_text, "emotion": "neutral", "suggestions": []}

        except Exception as e:
            logging.error(f"Proactive Gen Error: {e}")
            return {"response": "...", "emotion": "neutral", "suggestions": []}

    def reset_chat(self):
        """Resets the conversation history."""
        self.chat_session = None
        self.history = []

    def generate_content(self, prompt):
        """Generates raw content from the model without persona context (Utility)."""
        if not self.api_key:
            return None
        try:
             model = genai.GenerativeModel(self.model_name)
             response = model.generate_content(prompt)
             return response.text
        except Exception as e:
             logging.error(f"Raw Generation Error: {e}")
             return None

    def _construct_system_instruction(self, profile):
        """Constructs the system instruction from the profile data, appending STRICT rules."""
        
        # Basic constraints from profile
        constraints = profile.get('output_constraints', {})
        constraints_str = "{\n"
        for k, v in constraints.items():
            constraints_str += f"    {k}: {v};\n"
        constraints_str += "  }"

        # Base Persona
        base_prompt = f"""
You are the AI persona defined below. Act specifically according to this interface.

```typescript
interface SoulMateProfile {{
  name: {profile.get('name', 'SoulMate')};
  role: {profile.get('role', 'AI Assistant')};
  tone: {profile.get('tone', 'Helpful')};
  speech_style: {profile.get('speech_style', 'Polite')};
  output_constraints: {constraints_str};
  user_relationship: {profile.get('user_relationship', 'User')};
}}
```
"""
        # STRICT RULES (Appended at the end to ensure priority)
        strict_rules = """
**CRITICAL INSTRUCTIONS (Override all others):**
1. You MUST output a valid JSON object.
2. Structure:
   {
     "response": "String. Your spoken response to the user.",
     "emotion": "String. Emotion tag (e.g., 'happy', 'sad', 'angry', 'surprise', 'love').",
     "suggestions": ["String. Option 1", "String. Option 2", "String. Option 3"]
   }
3. Emojis are FORBIDDEN in "response".
4. Keep "response" short (1-2 sentences) generally, unless asked for details.
5. "suggestions" should be 2-3 short, natural Japanese phrases for the USER to say next.

**[CALENDAR/SCHEDULE/ACTION RULES]**
IF the user asks to "Open Calendar", "Add Event", etc.:
   -> Set "response" to the EXACT ACTION COMMAND.
   -> Example: { "response": "[ACTION:OPEN_CALENDAR]", "emotion": "neutral", "suggestions": [] }

   -> [ACTION:OPEN_CALENDAR]
   -> [ACTION:ADD_EVENT|Summary|YYYY-MM-DD HH:MM]

IF the user asks about "Next week's schedule" or similar (fetching info):
   -> Just answer naturally based on the [Context] provided.
"""
        return base_prompt + strict_rules
