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

    def configure(self, api_key, model_name="gemini-2.5-flash-lite", system_instruction=None):
        """Configures the AI Engine with new settings."""
        self.api_key = api_key
        self.model_name = model_name
        
        if system_instruction:
            self.system_instruction = system_instruction
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.chat_session = None 
                logging.info(f"AIEngine configured with model: {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to configure Gemini API: {e}")

    def set_system_prompt(self, prompt_text):
        """Updates the system prompt and resets the session."""
        logging.info("Updating System Prompt from Persona.")
        self.system_instruction = prompt_text
        # Reset chat session to apply new system instruction
        self.chat_session = None
        self.history = []

    def generate_response(self, message, context=None):
        """Generates a JSON response for the given message, or raw text if Action."""
        if not self.api_key:
            return "設定画面でGoogle Gemini APIキーを設定してください。"


        try:
            # Initialize Chat Session if needed
            if self.chat_session is None:
                response_schema = {
                    "type": "OBJECT",
                    "properties": {
                        "response": {"type": "STRING"},
                        "emotion": {"type": "STRING"},
                        "suggestions": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": ["response", "suggestions"]
                }
                
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction,
                    generation_config={
                        "response_mime_type": "application/json", 
                        "response_schema": response_schema
                    }
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
            # Send Message (Attempt 1: JSON Mode)
            try:
                response = self.chat_session.send_message(full_message)
                raw_text = response.text
                logging.info(f"raw_text from Gemini: {raw_text}")
            except Exception as e:
                logging.warn(f"Gemini Gen1 Error: {e}")
                raw_text = ""
            
            # Attempt 2: Fallback to Text Mode if empty
            if not raw_text.strip():
                logging.warn("Empty response from JSON Mode. Retrying with Text Mode...")
                try:
                     # Override config for this call
                     response = self.chat_session.send_message(
                         full_message + "\n(Please respond in plain JSON format.)",
                         generation_config={"response_mime_type": "text/plain"}
                     )
                     raw_text = response.text
                     logging.info(f"raw_text from Gemini (Fallback): {raw_text}")
                except Exception as e:
                     logging.error(f"Gemini Gen2 Error: {e}")
            
            # --- Parsing Logic ---
            try:
                # Cleanup markdown code blocks if present (common in Text Mode)
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                     clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                     clean_text = clean_text[:-3]
                
                # 1. Try passing as JSON directly
                data = json.loads(clean_text)
                return data 
            except json.JSONDecodeError:
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
                response_schema = {
                    "type": "OBJECT",
                    "properties": {
                        "response": {"type": "STRING"},
                        "emotion": {"type": "STRING"},
                        "suggestions": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": ["response", "suggestions"]
                }
                
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.system_instruction,
                    generation_config={
                        "response_mime_type": "application/json", 
                        "response_schema": response_schema
                    }
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
            # Send (Simulation)
            try:
                response = self.chat_session.send_message(full_message)
                raw_text = response.text
                logging.info(f"raw_text (Proactive) from Gemini: {raw_text}")
            except Exception as e:
                logging.warn(f"Proactive Gen1 Error: {e}")
                raw_text = ""

            # Attempt 2: Fallback
            if not raw_text.strip():
                 logging.warn("Empty response from (Proactive). Retrying with Text Mode...")
                 try:
                     response = self.chat_session.send_message(
                         full_message + "\n(Please respond in plain JSON format.)",
                         generation_config={"response_mime_type": "text/plain"}
                     )
                     raw_text = response.text
                     logging.info(f"raw_text (Proactive Fallback): {raw_text}")
                 except Exception as e:
                     logging.error(f"Proactive Gen2 Error: {e}")

            # Parsing
            try:
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                     clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                     clean_text = clean_text[:-3]

                data = json.loads(clean_text)
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


