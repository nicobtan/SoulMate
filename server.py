import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Imports from src
from src.core.config_manager import ConfigManager
from src.services.ai_engine import AIEngine
from src.services.calendar_manager import CalendarManager
from src.services.calendar_manager import CalendarManager
from src.services.memory_manager import MemoryManager
from src.services.history_manager import HistoryManager
# from src.services.active_engine import ActiveEngine # Optional
from src.services.tts_engine import TTSEngine

from src.api.base import BaseApiMixin
from src.api.chat_api import ChatApiMixin
from src.api.settings_api import SettingsApiMixin
from src.api.user_api import UserApiMixin

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

from src.services.user_manager import UserManager
import re

def extract_json_from_text(text):
    """
    AIの回答から有効なJSONオブジェクトを強力に抽出する（スタック解析アプローチ）
    """
    # 1. Markdownのコードブロック記法を除去 (単純化)
    cleaned_text = re.sub(r'```json\s*', '', text)
    cleaned_text = re.sub(r'```', '', cleaned_text)

    # 2. 候補探索: すべての '{' と '}' の位置を特定
    # これにより、ネストされたJSONや、テキストに埋もれたJSONを見つけ出す
    candidates = []
    
    # 単純な総当たりだとO(N^2)になるが、テキストは短いので許容
    start_indices = [i for i, char in enumerate(text) if char == '{']
    
    for start in start_indices:
        # このstart以降にある すべての '}' を試す
        # バランスが取れているか確認する簡易ロジックでもよいが、
        # json.loads() に任せるのが最も確実。
        # 効率のため、後ろから探す（長いマッチを優先したい場合）
        
        # text[start:] の中で '}' を探す
        fragment = text[start:]
        end_indices = [i for i, char in enumerate(fragment) if char == '}']
        
        for end_rel in end_indices:
            # text上の絶対位置
            end_abs = start + end_rel + 1
            
            candidate_str = text[start:end_abs]
            
            # 最低限の長さチェック
            if len(candidate_str) < 5: 
                continue
                
            try:
                # strict=False allows control characters like newlines within strings
                data = json.loads(candidate_str, strict=False)
                # 3. 構造チェック: "response" キーが含まれているか？
                if isinstance(data, dict) and "response" in data:
                    candidates.append(data)
            except:
                continue

    if not candidates:
        return None
        
    # 4. 最も情報量が多い（文字列長が長い）候補を採用する
    # これは {"response": "short"} よりも {"response": "long...", "suggestions": [...]} を優先するため
    # ただし、JSON文字列自体の長さではなく、辞書の中身の豊富さで判断したいが、
    # 単純にJSON文字列の長さで概ね正解できる。
    # (本当は suggestions があるほうを優先したい)
    
    best_candidate = max(candidates, key=lambda x: len(json.dumps(x)))
    return best_candidate

# --- Headless API Class ---
class HeadlessApi(ChatApiMixin, SettingsApiMixin, UserApiMixin, BaseApiMixin):
    def __init__(self):
        self._window = None # No GUI
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self.calendar_manager = CalendarManager()
        self.calendar_manager = CalendarManager()
        self.memory_manager = MemoryManager()
        self.history_manager = HistoryManager()
        
        # Init User Manager (Profile)
        # Init User Manager (Profile)
        self.user_manager = UserManager()
        
        # Init Interest Manager
        from src.services.interest_manager import InterestManager
        self.interest_manager = InterestManager()
        
        # Init Memory Service (Long-term)
        from src.services.memory_service import MemoryService
        self.memory_service = MemoryService(self._ai_engine)
        
        # Init Persona Manager
        from src.services.persona_manager import PersonaManager
        self._persona_manager = PersonaManager()
        
        # Load Persona from Config
        settings = self._config_manager.get_all()
        current_persona = settings.get('current_persona_id', 'default')
        
        persona_data = self._persona_manager.load_persona(current_persona)
        if persona_data:
            # MIXIN context: Managed by MemoryService (Profile + Facts)
            base_prompt = persona_data.get('system_prompt', '')
            mem_context = self.memory_service.get_combined_context()
            
            self._ai_engine.set_system_prompt(f"{base_prompt}\n{mem_context}")
            logger.info(f"Initial Persona Loaded: {current_persona} with Memory Context")
        
        self.active_engine = None # Disable active engine for server mode initially
        
        # Init TTS
        base_dir = os.getcwd()
        key_path = os.path.join(base_dir, "settings", "google-credentials.json")
        try:
            self.tts_engine = TTSEngine(key_path=key_path)
            logger.info("TTS Engine initialized.")
        except Exception as e:
            logger.error(f"TTS Init Failed: {e}")
            self.tts_engine = None


        # Configure AI
        settings = self._config_manager.get_all()
        self._configure_ai(settings)
        
    def log_to_debug(self, message, level='info'):
        """Override to log to console instead of GUI"""
        print(f"[{level.upper()}] {message}")

    def _configure_ai(self, settings):
        """Helper to configure engines with JSON mode support and Persona"""
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        persona_id = settings.get('current_persona_id', 'default')

        # 1. Base Prompt (Persona)
        base_prompt = ""
        if self.persona_manager:
            data = self.persona_manager.load_persona(persona_id)
            if data:
                base_prompt = data.get('system_prompt', '')
            else:
                base_prompt = "You are a helpful AI."

        # 2. User Profile Context - INTEGRATION (Memory Service)
        user_context = ""
        if self.memory_service:
            user_context = self.memory_service.get_combined_context()

        # 3. Topic Guidance
        topic_instruction = """
Guidance for conversation:
- Use the [User Profile] information to proactively suggest topics when the user is silent or asks for a topic.
- E.g., If the user likes 'Arknights', ask about their favorite character.
- E.g., If they are working on 'SoulMate project', ask about the specific progress.
"""

        # 4. Citation Rule (URL Requirement)
        citation_instruction = """
Guideline for Citations:
When you mention specific news, videos, or articles found via Google Search (Grounding), **YOU MUST INCLUDE THE URL** of the source.
- Never describe a specific content without providing its link.
- Format: "... description ... (Source: [URL])".
"""

        # 4. JSON Mode Instruction
        json_instruction = """
Response Format: JSON
You MUST respond in the following JSON format:
{
    "response": "Your spoken response text here.",
    "suggestions": ["Option 1", "Option 2", "Option 3"]
}
"""
        
        # 5. Combine All
        # Note: We do NOT use set_system_prompt here because AIEngine needs to manage it session-wise?
        # Ideally, we update the system_instruction in default config or re-init chat.
        # But AIEngine.configure doesn't take system_prompt. AIEngine.set_system_prompt does.
        
        full_system_prompt = f"{base_prompt}\n{user_context}\n{topic_instruction}\n{citation_instruction}\n\n{json_instruction}"
        
        if self._ai_engine:
            # Set the combined prompt
            self._ai_engine.set_system_prompt(full_system_prompt)
            
            # Configure Key/Model
            self._ai_engine.configure(
                api_key=api_key, 
                model_name=model
            )
            logger.info(f"AI Configured: {model} with User Profile")

            logger.info(f"AI Configured: {model} with User Profile")

    def chat(self, message):

        logger.info(f"Chat Request: {message}")
        
        # 1. AI生成
        if not self._ai_engine:
             return {"text": "AI Engine Not Ready", "audio": None, "suggestions": []}

        raw_response = self._ai_engine.generate_response(message)
        
        # 2. JSONパース (強化版)
        text_to_speak = ""
        suggestions = []
        
        # まずは辞書チェック (通常ありえないが念のため)
        if isinstance(raw_response, dict):
             parsed_data = raw_response
        else:
             # 文字列から抽出
             parsed_data = extract_json_from_text(str(raw_response))
        
        if parsed_data:
            # 成功！JSONの中身("response")だけを使う
            text_to_speak = parsed_data.get("response", str(raw_response))
            suggestions = parsed_data.get("suggestions", [])
        else:
            # Fallback (Parse Failed): Desperation Mode
            clean_text = str(raw_response)
            
            # 1. Basic Markdown Cleanup
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[0]
            if "```" in clean_text:
                 clean_text = clean_text.split("```")[0]

            # 2. Aggrative Structural Cleanup (Line-based)
            lines = clean_text.split('\n')
            final_lines = []
            for line in lines:
                s = line.strip()
                # Stop if line is structural closing alone
                if s in ['}', ']', ']}', '}]', '```', '```json']:
                    break
                # Stop if line looks like a leaked list item (Start/end quote + comma/bracket)
                if (s.startswith('"') or s.startswith("'")) and (s.endswith(',') or s.endswith(']')):
                    break
                
                final_lines.append(line)
            
            clean_text = '\n'.join(final_lines).strip()
            
            # 3. Final trim of trailing brackets attached to text
            if len(clean_text) > 0 and clean_text[-1] in [']', '}']:
                 clean_text = clean_text.rstrip(']} \t\n')

            text_to_speak = clean_text
            suggestions = []
            

        # 3. 音声生成
        audio_path = None
        if self.tts_engine:
            try:
                # URLなどを除去してクリーンにする
                import re
                clean_text = re.sub(r'http[s]?://\S+', '', text_to_speak)
                # 音声生成
                voice = self.config_manager.get('voice_type', 'ja-JP-Neural2-B')
                output_dir = os.path.join(os.getcwd(), 'dist/audio')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                audio_path = self.tts_engine.generate_voice(
                    clean_text, 
                    output_dir=output_dir, 
                    voice_name=voice
                )
            except Exception as e:
                logger.error(f"TTS Error: {e}")

        # 4. Return Data
        # 履歴保存（HistoryManagerの呼び出し）
        if self.history_manager:
             self.history_manager.add_message("ai", text_to_speak)

        return {
            "text": text_to_speak,
            "audio": audio_path,
            "suggestions": suggestions
        }

    """Returns list of available personas."""
    def get_persona_list(self):
        return self._persona_manager.list_personas()

    def change_persona(self, persona_id):
        """Switches the current persona."""
        logger.info(f"Switching persona to: {persona_id}")
        data = self._persona_manager.load_persona(persona_id)
        
        if not data:
            return {"status": "error", "message": "Persona not found"}
            
        # Changing persona requires re-building the full prompt (Persona + User + Format)
        # So we trigger _configure_ai again essentially, or just rebuild prompt.
        
        # Update config first
        self.config_manager.config['current_persona_id'] = persona_id
        self.config_manager.save()
        
        # Re-run configuration to merge new persona with user profile
        self._configure_ai(self.config_manager.get_all())
        
        return {"status": "success", "name": data.get('name', persona_id)}


    @app.post("/api/settings")
    async def save_settings_endpoint(settings: dict):
        """Updates server configuration."""
        if not server_api:
            raise HTTPException(status_code=500, detail="Server not initialized")
        
        # Update ConfigManager
        server_api.config_manager.config.update(settings)
        server_api.config_manager.save()
        
        # Re-configure AI
        server_api._configure_ai(server_api.config_manager.config)
        
        # PUSH CONFIG TO BUBBLE SERVICE (NEW)
        if server_api.bubble_service:
            server_api.bubble_service.update_settings(server_api.config_manager.config)
        
        return {"status": "ok", "config": server_api.config_manager.get_all()}
        
    def dismiss_bubble(self, action_id):
        """API: Dismiss a bubble and refill."""
        if self.bubble_service:
            # 1. Remove it logic
            removed = self.bubble_service.remove_bubble(action_id)
            if removed:
                # 2. Trigger Refill logic (This will now fill up to MAX due to service update)
                new_bubble = self.bubble_service.refill_bubbles()
                return {"status": "success", "refilled": new_bubble is not None, "bubble": new_bubble}
        return {"status": "error"}

    def force_talk(self):
        """ピンクボタンの処理: 検索ベースの話題提供 (Grounded Force Talk)"""
        logger.info("[HeadlessApi] Processing Grounded Force Talk...")
        
        if not self._ai_engine:
            return {"text": "Error: AI Engine not ready", "audio": None}

        # 1. ユーザー情報を取得
        user_context = ""
        if hasattr(self, 'user_manager') and self.user_manager:
            user_context = self.user_manager.get_profile_context()

        # 2. 検索トピックの取得
        import random
        search_topic_instruction = ""
        if hasattr(self, 'interest_manager') and self.interest_manager:
            topics = self.interest_manager.load_topics()
            if topics:
                chosen_topic = random.choice(topics)
                search_topic_instruction = f"""
[Grounding Instruction]
The user is interested in: "{chosen_topic}".
**USE GOOGLE SEARCH** to find the latest news or updates (today/this week) about "{chosen_topic}".
Then, tell the user about it in your persona's tone.
If no recent news is found, talk about general facts regarding "{chosen_topic}".
"""
            else:
                 search_topic_instruction = "Use Google Search to find a trending technology news topic."
        
        # 3. プロンプト構築
        prompt = f"""
[Situation]
The user is silent. You want to start a conversation about something NEW and EXCITING using external information.

[User Profile]
{user_context}

{search_topic_instruction}

[Output Requirement]
- Use your Persona's tone.
- Keep it concise usually (2-3 sentences), but provide details if requested.
- Ask a follow-up question.
        # 4. チャットとして処理
        return self.chat(prompt)

    def restore_history(self):
        """API: Restore session history."""
        # Use print for guaranteed visibility
        print(f"[HeadlessApi] restore_history called.")
        if self.history_manager:
            history = self.history_manager.get_session_history()
            print(f"[HeadlessApi] Returning {len(history)} messages for restore.")
            return history
        print("[HeadlessApi] History manager not initialized.")
        return []

    def debug_log(self, message: str):
        """Exposed for frontend logging via pywebview."""
        print(f"[CLIENT LOG] {message}")
        return {"status": "ok"}
        
server_api = None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global server_api
    from src.services.persona_manager import PersonaManager
    
    logger.info("Initializing SoulMate Server API...")
    try:
        # Re-init Server API with all components
        server_api = HeadlessApi()
        
        # Manually attach PersonaManager BEFORE configuration
        server_api.persona_manager = PersonaManager()
        
        # Configure AI (Safe now)
        settings = server_api.config_manager.get_all()
        server_api._configure_ai(settings)
        
        logger.info("SoulMate Headless API Ready")
    except Exception as e:
        logger.error(f"Startup Failed: {e}")
        server_api = None
    
    yield
    
    logger.info("Shutting down SoulMate Server...")

# --- FastAPI App ---
app = FastAPI(title="SoulMate Server", lifespan=lifespan)

class ChatRequest(BaseModel):
    text: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    response_data = server_api.chat(req.text)
    
    # Process Audio Path -> URL
    # response_data['audio'] is absolute path. We need to convert to /audio/filename
    if response_data.get('audio'):
        abs_path = response_data['audio']
        filename = os.path.basename(abs_path)
        response_data['audio'] = f"/audio/{filename}"
        
    return response_data

@app.get("/api/settings")
async def settings_endpoint():
    """Returns current server configuration (for syncing mobile/web clients)."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    # Return all config
    return server_api.config_manager.get_all()

@app.post("/api/settings")
async def save_settings_endpoint(settings: dict):
    """Updates server configuration."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    # Update ConfigManager
    # Assuming config_manager.config is the dict we update
    # We need to see if config_manager has an update method, but modifying .config and calling .save() usually works
    # Based on view_file usage:
    server_api.config_manager.config.update(settings)
    server_api.config_manager.save()
    
    # Re-configure AI (Important for API Key)
    server_api._configure_ai(server_api.config_manager.config)
    
    return {"status": "ok", "config": server_api.config_manager.get_all()}

@app.post("/api/force_talk")
async def force_talk_endpoint():
    """Triggers a proactive message from the AI."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    logger.info("[Force Talk] Triggered via API") # Added Log

    # Call force_talk logic
    if hasattr(server_api, 'force_talk'):
        return server_api.force_talk()
    else:
        return {"text": "Error: force_talk not implemented", "audio": None}

class LogRequest(BaseModel):
    message: str

@app.post("/api/debug_log")
async def debug_log_endpoint(req: LogRequest):
    """Prints client-side logs to the server terminal."""
    logger.info(f"[CLIENT LOG] {req.message}")
    return {"status": "ok"}

@app.get("/api/calendar")
async def calendar_endpoint():
    if not server_api or not server_api.calendar_manager:
        return {"events": []}
    
    # Mock authentication check or reuse logic
    if server_api.calendar_manager.is_authenticated:
        events = server_api.calendar_manager.get_upcoming_events()
        return {"events": events}
    return {"events": [], "error": "Not authenticated"}

@app.get("/api/personas")
async def get_personas_endpoint():
    """Returns list of available personas."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return server_api.get_persona_list()

class ChangePersonaRequest(BaseModel):
    persona_id: str

@app.post("/api/persona/change")
async def change_persona_endpoint(req: ChangePersonaRequest):
    """Switches the current persona."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    result = server_api.change_persona(req.persona_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result

@app.get("/api/history")
async def get_history_endpoint(limit: int = 50):
    """Returns recent chat history."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    return server_api.get_history(limit=limit)

@app.get("/api/history/restore")
async def restore_history_endpoint():
    """Returns formatted session history for UI restore."""
    if not server_api:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return server_api.restore_history()

# Helper to serve audio files specifically (if they are in dist/audio)
# We handle this via StaticFiles mount

# Mount 'dist' as root for static files (Frontend)
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
