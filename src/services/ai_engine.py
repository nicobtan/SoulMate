import logging
import datetime
import json
import re
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        self.api_key = None
        self.model_name = "gemini-2.5-flash-lite"
        self.client = None
        self.chat_session = None
        self.history = [] # Local history storage if needed, or rely on chat_session object?
        # New SDK chat_session (client.chats.create) maintains its own history.
        
        self.system_instruction = "You are a helpful AI assistant."

    def configure(self, api_key, model_name=None, system_instruction=None):
        """Configures the AI Engine with new settings."""
        self.api_key = api_key
        if model_name:
            self.model_name = model_name
        
        if system_instruction:
            self.system_instruction = system_instruction
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.chat_session = None 
                logging.info(f"AIEngine configured with new SDK. Model: {self.model_name}")
            except Exception as e:
                logging.error(f"Failed to configure Gemini Client: {e}")

    def set_system_prompt(self, prompt_text):
        """Updates the system prompt and resets the session."""
        logging.info("Updating System Prompt from Persona.")
        self.system_instruction = prompt_text
        self.chat_session = None

    def _get_chat_session(self, tools=None):
        """Initializes or returns the chat session."""
        if self.chat_session is None:
            if not self.client:
                raise ValueError("Client not initialized. Call configure() first.")

            # Config
            # Note: With Grounding, strict JSON schema might conflict or be unsupported on 2.5-flash-lite currently.
            # We revert to text/plain and rely on prompt instruction for JSON.
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                response_mime_type="text/plain", 
                tools=tools
            )

            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=config,
                history=self.history 
            )
        return self.chat_session

    def _parse_json_response(self, raw_text):
        """Extracts JSON from text even if there is conversational filler."""
        if not raw_text:
            return {"response": "...", "emotion": "neutral", "suggestions": []}

        try:
            # 1. Try to find code block first
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 2. Fallback: Try to find the first '{' and last '}'
                # This handles cases where code blocks are missing but JSON is present
                start = raw_text.find('{')
                end = raw_text.rfind('}')
                if start != -1 and end != -1:
                    json_str = raw_text[start:end+1]
                else:
                    # No JSON found, treat as plain text if it looks like a response
                    return {"response": raw_text.strip(), "emotion": "neutral", "suggestions": []}

            return json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            logging.warn(f"JSON Parse Failed: {e}. Raw: {raw_text[:50]}...")
            # Fallback: Treat entire text as response
            clean_text = raw_text.strip()
            # Remove markdown code blocks if any remain
            clean_text = clean_text.replace("```json", "").replace("```", "")
            return {"response": clean_text, "emotion": "neutral", "suggestions": []}

    def generate_response(self, message, context=None, image=None):
        """Generates a JSON response for the given message."""
        if not self.api_key:
            return {"response": "設定画面でGoogle Gemini APIキーを設定してください。", "emotion": "neutral", "suggestions": []}

        try:
            # Context Construction (Shared)
            now = datetime.datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Simple Time Segment
            hour = now.hour
            time_segment = "Night"
            if 5 <= hour < 11: time_segment = "Morning"
            elif 11 <= hour < 16: time_segment = "Daytime"
            elif 16 <= hour < 19: time_segment = "Evening"
            elif 19 <= hour < 23: time_segment = "Night"
            
            base_context = f"Current Time: {now_str} ({time_segment})\n"
            if context:
                base_context += f"{context}\n"
            
            # System Prompt (JSON Requirement)
            system_prompt_add = """
[SYSTEM REMINDER]
JSON Output Required! 
Format: {"response": "string", "emotion": "string", "suggestions": ["string", "string"]}
Key "suggestions": Provide 2-3 short, natural Japanese response options.
"""
            
            # --- BRANCH: VISION MODE (Stateless) ---
            if image:
                logging.info("Vision request detected: Using stateless generate_content")
                
                # Check for empty or tag-only message
                # If message is empty or just standard tags, give a default instruction
                vision_instruction = message
                if not message or message.strip() in ["[Screen]", "[Clipboard]", ""]:
                    vision_instruction = "Please analyze this image and describe what you see."
                elif message.strip().startswith("[") and len(message.strip()) < 20: 
                     # Heuristic: If short tag-like message, treat as needing description
                     vision_instruction = f"{message} Please analyze this image."

                # Vision Prompt with Strong Override
                full_message = f"""
[Context]
{base_context}

[Instruction]
You are currently in **Vision Mode**. You CAN see the attached image.
Ignore any previous instructions stating you cannot see images.
Please answer the user's request based on the image.

[User Request]
{vision_instruction}

{system_prompt_add}
"""
                # Disable tools (Search) for Vision
                run_config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="text/plain", 
                    tools=[] 
                )
                
                # Stateless Generation
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[full_message, image],
                    config=run_config
                )
                
            # --- BRANCH: CHAT MODE (Stateful / Grounding) ---
            else:
                # Tools (Grounding) Enable
                # Enable Grounding for all chat interactions? Or just Smart Talk?
                # User wants grounding. Enable it.
                tools = [types.Tool(google_search=types.GoogleSearch())]
                session = self._get_chat_session(tools=tools)

                full_message = f"""
[Context/Memory]
{base_context}

[User Input]
{message}

{system_prompt_add}
"""
                # Stateful Send
                response = session.send_message(full_message)

            # Common Response Parsing
            raw_text = response.text
            logging.info(f"raw_text: {raw_text}")
            
            return self._parse_json_response(raw_text)

        except Exception as e:
            logging.error(f"Generation Error: {e}")
            return {"response": f"エラー: {str(e)}", "emotion": "sad", "suggestions": []}

    def reset_chat(self):
        self.chat_session = None
        self.history = []

    def generate_content(self, prompt):
        """Raw content generation utility."""
        if not self.client: return None
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logging.error(f"Raw Gen Error: {e}")
            return None
