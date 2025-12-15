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
from src.services.memory_manager import MemoryManager
# from src.services.active_engine import ActiveEngine # Optional
from src.services.tts_engine import TTSEngine

from src.api.base import BaseApiMixin
from src.api.chat_api import ChatApiMixin
from src.api.settings_api import SettingsApiMixin

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# --- Headless API Class ---
class HeadlessApi(ChatApiMixin, SettingsApiMixin, BaseApiMixin):
    def __init__(self):
        self._window = None # No GUI
        self.config_manager = ConfigManager()
        self.ai_engine = AIEngine()
        self.calendar_manager = CalendarManager()
        self.memory_manager = MemoryManager()
        
        # Init Persona Manager
        from src.services.persona_manager import PersonaManager
        self.persona_manager = PersonaManager()
        
        # Load Persona from Config
        settings = self._config_manager.get_all()
        current_persona = settings.get('current_persona_id', 'default')
        
        persona_data = self._persona_manager.load_persona(current_persona)
        if persona_data:
            self._ai_engine.set_system_prompt(persona_data.get('system_prompt', ''))
            logger.info(f"Initial Persona Loaded: {current_persona}")
        
        self.active_engine = None # Disable active engine for server mode initially
        
        # Init TTS
        base_dir = os.getcwd()
        cred_path = os.path.join(base_dir, 'google-credentials.json')
        try:
            self.tts_engine = TTSEngine(key_path="google-credentials.json")
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
        
        # Note: server_api initializes with Default Persona.
        # Calling configure with system_instruction=None keeps the current one (from set_system_prompt).
        
        if self.ai_engine:
            self.ai_engine.configure(
                api_key=api_key, 
                model_name=model
            )
            logger.info(f"AI Configured: {model}")

    def get_persona_list(self):
        """Returns list of available personas."""
        return self._persona_manager.list_personas()

    def change_persona(self, persona_id):
        """Switches the current persona."""
        logger.info(f"Switching persona to: {persona_id}")
        data = self._persona_manager.load_persona(persona_id)
        
        if not data:
            return {"status": "error", "message": "Persona not found"}
            
        self._ai_engine.set_system_prompt(data.get('system_prompt', ''))
        
        # Save to Config
        self.config_manager.config['current_persona_id'] = persona_id
        self.config_manager.save()
        
        return {"status": "success", "name": data.get('name', persona_id)}

    # ★ここが修正ポイント: チャット処理をオーバーライドしてJSONをパースする
    def chat(self, message):

        logger.info(f"Chat Request: {message}")
        
        # 1. AI生成
        if not self.ai_engine:
             return {"text": "AI Engine Not Ready", "audio": None, "suggestions": []}

        raw_response = self.ai_engine.generate_response(message)
        
        # 2. JSONパース (AIEngineが既に辞書を返している場合はそれを使う)
        text_to_speak = ""
        suggestions = []
        
        if isinstance(raw_response, dict):
             text_to_speak = raw_response.get("response", "")
             suggestions = raw_response.get("suggestions", [])
        else:
            # 万が一文字列で返ってきた場合のフォールバック (基本は辞書のはず)
            text_to_speak = str(raw_response)
            try:
                clean_json = text_to_speak.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_json)
                if isinstance(data, dict):
                    text_to_speak = data.get("response", text_to_speak)
                    suggestions = data.get("suggestions", [])
            except (json.JSONDecodeError, AttributeError):
                pass 


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

        # 4. フロントエンドへ返すデータを構築
        # ここで suggestions を含めるのが重要！
        return {
            "text": text_to_speak,
            "audio": audio_path,
            "suggestions": suggestions # これが黄色ボタンの中身になります
        }

    def force_talk(self):
        """ピンクボタンの処理"""
        logger.info("[HeadlessApi] Processing Force Talk...")
        if not self.ai_engine:
            return {"text": "Error: AI Engine not ready", "audio": None}
            
        prompt = "（ユーザーは無言でこちらを見ています。何か話題を提供したり、気遣う言葉をかけてください）"
        # 上で修正した chat メソッドを呼ぶので、ここも自動的にJSON対応になります
        return self.chat(prompt)
        
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

# Helper to serve audio files specifically (if they are in dist/audio)
# We handle this via StaticFiles mount

# Mount 'dist' as root for static files (Frontend)
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
