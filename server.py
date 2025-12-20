import os
import logging
import datetime
import re
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

# Imports from src
from src.core.config_manager import ConfigManager
from src.services.ai_engine import AIEngine
from src.services.calendar_manager import CalendarManager
from src.services.history_manager import HistoryManager
from src.services.tts_engine import TTSEngine
from src.services.voice_service import VoiceService
from src.services.user_manager import UserManager
from src.services.interest_manager import InterestManager
from src.services.memory_service import MemoryService
from src.services.persona_manager import PersonaManager
from src.services.db_manager import DatabaseManager
from src.services.migration_service import MigrationService
from src import core_instance

from src.api.base import BaseApiMixin
from src.api.chat_api import ChatApiMixin
from src.api.settings_api import SettingsApiMixin
from src.api.user_api import UserApiMixin

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# --- Headless API Class (Logic Container) ---
class HeadlessApi(ChatApiMixin, SettingsApiMixin, UserApiMixin, BaseApiMixin):
    def __init__(self):
        self._window = None # No GUI
        self.services = self # Mixin Pattern: API instance itself is the service container
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self.calendar_manager = CalendarManager()
        self.history_manager = HistoryManager()
        self.user_manager = UserManager()
        self.interest_manager = InterestManager()
        self.memory_service = MemoryService(self._ai_engine)
        self._persona_manager = PersonaManager()
        
        # Load Persona
        settings = self._config_manager.get_all()
        current_persona = settings.get('current_persona_id', 'default')
        persona_data = self._persona_manager.load_persona(current_persona)
        
        if persona_data:
            base_prompt = persona_data.get('system_prompt', '')
            mem_context = self.memory_service.get_combined_context()
            self._ai_engine.set_system_prompt(f"{base_prompt}\n{mem_context}")
            logger.info(f"Initial Persona Loaded: {current_persona}")
        
        self.active_engine = None 
        
        # Init TTS & VoiceService
        base_dir = os.getcwd()
        key_path = os.path.join(base_dir, "settings", "google-credentials.json")
        try:
            self.tts_engine = TTSEngine(key_path=key_path)
            self.voice_service = VoiceService()
            logger.info("TTS & VoiceService initialized.")
        except Exception as e:
            logger.error(f"TTS/VoiceService Init Failed: {e}")

        # Configure AI
        self._configure_ai(settings)
        
    def log_to_debug(self, message, level='info'):
        print(f"[{level.upper()}] {message}")

    def _configure_ai(self, settings):
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        persona_id = settings.get('current_persona_id', 'default')

        base_prompt = ""
        if self._persona_manager:
            data = self._persona_manager.load_persona(persona_id)
            if data: base_prompt = data.get('system_prompt', '')

        user_context = ""
        if self.memory_service:
            user_context = self.memory_service.get_combined_context()

        topic_instruction = "Guidance: Use [User Profile] for proactive topics."
        citation_instruction = "Guideline: MUST include URL for search results."
        
        # ★ TOON (Token-Oriented Object Notation) Format Instruction
        format_instruction = """
Response Format:
You MUST respond using **TOON (Token-Oriented Object Notation)** format.
NO JSON. NO Markdown code blocks. Just plain text with indentation.

response: Your spoken response here. (Quotes and newlines allowed)
emotion: happy
suggestions:
  - Suggestion 1
  - Suggestion 2
  - Suggestion 3
  - Suggestion 4
  - 他の話題について

[Output Requirement]
- Use your Persona's tone.
- Keep it concise.
"""
        full_system_prompt = f"{base_prompt}\n{user_context}\n{topic_instruction}\n{citation_instruction}\n\n{format_instruction}"
        
        if self._ai_engine:
            self._ai_engine.set_system_prompt(full_system_prompt)
            self._ai_engine.configure(api_key=api_key, model_name=model)
            if self.voice_service and api_key:
                self.voice_service.set_api_key(api_key)

    def chat(self, message):
        logger.info(f"Chat Request: {message}")
        if not self._ai_engine:
             return {"text": "AI Engine Not Ready", "audio": None, "suggestions": []}

        # 1. Generate (AIEngine now handles TOON parsing)
        response_data = self._ai_engine.generate_response(message)
        
        text_to_speak = response_data.get("text", "")
        emotion = response_data.get("emotion", "neutral")
        suggestions = response_data.get("suggestions", [])
        grounding_info = response_data.get("grounding_info")

        # 2. TTS
        audio_path = None
        settings = self._config_manager.get_all()
        provider = settings.get('tts_provider', 'voicevox') 
        
        try:
            clean_text = re.sub(r'http[s]?://\S+', '', text_to_speak)
            output_dir = os.path.join(os.getcwd(), 'dist/audio')
            if not os.path.exists(output_dir): os.makedirs(output_dir)

            if provider == 'voicevox' and self.voice_service:
                voice = settings.get('voice_type', '3')
                audio_path = self.voice_service.generate_voice(clean_text, voice_name=voice)
            elif self.tts_engine:
                 voice = settings.get('voice_type', 'ja-JP-Neural2-B')
                 if provider == 'google' and len(str(voice)) < 3: voice = 'ja-JP-Neural2-B'
                 audio_path = self.tts_engine.generate_voice(clean_text, output_dir=output_dir, voice_name=voice)
        except Exception as e:
            logger.error(f"TTS Error: {e}")

        # 3. DB Save & History
        db = core_instance.get_db()
        if db:
            active = db.get_active_session()
            session_id = active['id'] if active else db.create_session()
            db.add_message(session_id, "user", message)
            db.add_message(session_id, "ai", text_to_speak, meta={"emotion": emotion, "suggestions": suggestions})
            
        if self.history_manager:
             self.history_manager.add_message("ai", text_to_speak)

        return {
            "text": text_to_speak,
            "audio": audio_path,
            "suggestions": suggestions,
            "emotion": emotion,
            "grounding_info": grounding_info
        }

    def force_talk(self):
        prompt = "The user is silent. Say something brief based on your persona and user profile."
        if self.user_manager:
             prompt += f"\nUser Context: {self.user_manager.get_profile_context()}"
        return self.chat(prompt)

    def get_persona_list(self):
        return self._persona_manager.list_personas()

    def change_persona(self, persona_id):
        data = self._persona_manager.load_persona(persona_id)
        if not data: return {"status": "error", "message": "Not found"}
        self._config_manager.config['current_persona_id'] = persona_id
        self._config_manager.save()
        self._configure_ai(self._config_manager.get_all())
        return {"status": "success", "name": data.get('name', persona_id)}

    def restore_history(self):
        if self.history_manager: return self.history_manager.get_session_history()
        return []

    def get_history(self, limit=50):
        db = core_instance.get_db()
        if db: return db.get_history(limit=limit)
        return []

# --- API Models ---
class ChatRequest(BaseModel):
    text: str

class ChangePersonaRequest(BaseModel):
    persona_id: str

# --- Global API Instance ---
server_api = None

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global server_api
    logger.info("Initializing SoulMate Server...")
    try:
        # DB Init
        db = DatabaseManager()
        db.init_db()
        core_instance.set_db(db)
        
        # Migration
        migration = MigrationService(db)
        migration.migrate_json_to_db()
        
        if not db.get_active_session():
            db.create_session("はじめまして")

        server_api = HeadlessApi()
        core_instance.set_api(server_api)
        logger.info("SoulMate Server Ready")
    except Exception as e:
        logger.error(f"Startup Failed: {e}")
    yield
    logger.info("Shutting down...")

# --- FastAPI App ---
app = FastAPI(title="SoulMate Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    res = server_api.chat(req.text)
    if res.get('audio'):
        res['audio'] = f"/audio/{os.path.basename(res['audio'])}"
    return res

@app.get("/api/settings")
async def get_settings():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api._config_manager.get_all()

@app.post("/api/settings")
async def save_settings(settings: dict):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    server_api._config_manager.config.update(settings)
    server_api._config_manager.save()
    server_api._configure_ai(server_api._config_manager.get_all())
    return {"status": "ok"}

@app.post("/api/force_talk")
async def force_talk():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.force_talk()

@app.get("/api/personas")
async def get_personas():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.get_persona_list()

@app.post("/api/persona/change")
async def change_persona(req: ChangePersonaRequest):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.change_persona(req.persona_id)

@app.get("/api/history")
async def get_history(limit: int = 50):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.get_history(limit=limit)

@app.get("/api/history/restore")
async def restore_history():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.restore_history()

# Static / Audio
os.makedirs("dist/audio", exist_ok=True)
app.mount("/audio", StaticFiles(directory="dist/audio"), name="audio")

if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
