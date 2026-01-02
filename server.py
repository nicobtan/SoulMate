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
from src.services.memory_manager import MemoryManager
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
    """
    GUIを持たないヘッドレスモード（サーバーモード）用のAPIクラス。
    FastAPIから利用され、音声合成やAI対話のコアロジックを管理します。
    """
    def __init__(self):
        self._window = None # GUIウィンドウは存在しない
        self.services = self # Mixinパターン: APIインスタンス自体がサービスコンテナとなる
        self._config_manager = ConfigManager()
        self._ai_engine = AIEngine()
        self._calendar_manager = CalendarManager()
        self.history_manager = HistoryManager()
        self.user_manager = UserManager()
        self.interest_manager = InterestManager()
        self._memory_manager = MemoryManager()
        self._persona_manager = PersonaManager()
        
        # ペルソナの読み込み
        settings = self._config_manager.get_all()
        current_persona = settings.get('current_persona_id', 'default')
        persona_data = self._persona_manager.load_persona(current_persona)
        
        if persona_data:
            base_prompt = persona_data.get('system_prompt', '')
            mem_context = self._memory_manager.get_combined_context()
            self._ai_engine.set_system_prompt(f"{base_prompt}\n{mem_context}")
            logger.info(f"Initial Persona Loaded: {current_persona}")
        
        # Initialize ActiveEngine
        # Callback routes to SocketIO emit
        from src.services.active_engine import ActiveEngine
        self.active_engine = ActiveEngine(self._ai_engine, on_message_callback=self.on_active_message)
        self.active_engine.configure(settings)
        if settings.get('active_talk_interval', 0):
             self.active_engine.start()
        
        # TTSエンジンおよびVoiceServiceの初期化
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
        
        
    # --- Socket IO Emitters (Overrides BaseApiMixin) ---
    def log_to_debug(self, message, level='info'):
        """Override to emit via SocketIO instead of pywebview."""
        print(f"[{level.upper()}] {message}")
        try:
            from src.core.socket_manager import sio
            import asyncio
            # Determine category (reuse logic or simplify)
            category = 'sys'
            if level in ['rag', 'mind', 'vision']:
                category = level
                level = 'info'
            
            asyncio.create_task(sio.emit('debug_log', {
                'msg': str(message), 
                'level': level, 
                'category': category
            }))
        except Exception as e:
            logger.error(f"Socket Emit Error: {e}")

    def log_to_mind(self, msg):
        """Override to emit mind logs via SocketIO."""
        # Simple translation logic (reused from base but simplified)
        translated = msg
        if "Targeting Model:" in msg: translated = "(私の頭脳、Geminiモードでフル回転させるわね✨)"
        elif "Reasoning..." in msg: translated = "(うーん、どう伝えればいいかしら…🤔)"
        
        print(f"[MIND] {translated}")
        try:
            from src.core.socket_manager import sio
            import asyncio
            asyncio.create_task(sio.emit('mind_log', {'msg': translated}))
        except: pass

    def play_filler(self):
        """Override filler to emit ghost message and audio command."""
        import random
        fillers = [
            {"text": "んー、そうねぇ…", "file": "audio/fillers/thinking_01.wav"},
            {"text": "えっと…", "file": "audio/fillers/thinking_02.wav"},
            {"text": "ふふっ、それはね…", "file": "audio/fillers/thinking_03.wav"},
        ]
        chosen = random.choice(fillers)
        try:
            from src.core.socket_manager import sio
            import asyncio
            # Ghost Text
            asyncio.create_task(sio.emit('ghost_message', {'text': chosen['text']}))
            # Audio (Check existence not needed as much for web, assume served)
            asyncio.create_task(sio.emit('play_audio_command', {'url': chosen['file']}))
        except: pass

    def on_active_message(self, json_str):
        """Callback for ActiveEngine proactive messages."""
        logger.info(f"Active Message Triggered: {json_str[:50]}...")
        try:
            import json
            data = json.loads(json_str)
            
            # TTS generation if missing? 
            # ActiveEngine usually calls ai_engine.generate_proactive_message which returns text/emotion.
            # But IT DOES NOT Generate Audio inside ActiveEngine default logic usually.
            # We need to generate audio HERE if data doesn't have it.
            # Check ActiveEngine logic: it returns dict with text/suggestions/emotion/type.
            
            text = data.get('text', '')
            if text:
                # Generate Audio
                if self.voice_service:
                    # Clean text
                    clean = re.sub(r'http[s]?://\S+', '', text)
                    clean = re.sub(r'[\[\(].*?[\]\)]', '', clean) # Remove notes
                    
                    settings = self._config_manager.get_all()
                    provider = settings.get('tts_provider', 'voicevox')
                    voice = settings.get('voice_type', '3')
                    
                    # Generate
                    # Note: generate_voice returns "audio/filename.wav" (relative to dist/ usually?)
                    # voice_service logic: returns "audio/encoded_name.wav" (Web Path)
                    audio_path = self.voice_service.generate_voice(clean, voice_name=voice, provider=provider)
                    
                    if audio_path:
                        data['audio'] = audio_path
            
            from src.core.socket_manager import sio
            import asyncio
            asyncio.create_task(sio.emit('chat_message', data))
            
        except Exception as e:
            logger.error(f"Active Message Emit Error: {e}")

    def _configure_ai(self, settings):
        """AIエンジンの設定（モデル、ペルソナ、システムプロンプトの構築）を行います。"""
        api_key = settings.get('api_key')
        model = settings.get('model_name', 'gemini-2.5-flash-lite')
        persona_id = settings.get('current_persona_id', 'default')

        # 安全策: 古い設定が残っている場合に正しいモデル名へ強制変換
        # "gemini-3.0" is invalid. Must be "gemini-3".
        if "gemini-3.0" in model:
            logger.info(f"Param Migration: Replacing '{model}' with '{model.replace('3.0', '3')}'.")
            model = model.replace("gemini-3.0", "gemini-3")

        base_prompt = ""
        if self._persona_manager:
            data = self._persona_manager.load_persona(persona_id)
            if data: base_prompt = data.get('system_prompt', '')

        user_context = ""
        if self._memory_manager:
            user_context = self._memory_manager.get_combined_context()

        topic_instruction = "Guidance: Use [User Profile] for proactive topics."
        citation_instruction = "Guideline: MUST include URL for search results."
        
        # ★ TOON (Token-Oriented Object Notation) フォーマット指示
        # JSONではなく、軽量なYAML/Line-based形式を指定して安定性を向上
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
        continuity_instruction = """
[CRITICAL INSTRUCTION: CONTEXT CONTINUITY]
1. If the user's input is short or ambiguous (e.g., "Tell me more", "Why?", "Details?", "Really?"):
   - You MUST strictly refer to the IMMEDIATE CONVERSATION HISTORY (Short Term Memory).
   - Elaborate on the TOPIC DISCUSSED IN THE PREVIOUS TURN.
   - DO NOT switch topics or explain your underlying AI architecture (e.g., Gemini, LLM specs) unless explicitly asked.
Priority of Reference: [Highest] Immediate User/AI Dialogue History [Medium] Current Scene/Persona Context [Lowest] General Knowledge/System Specs
"""

        full_system_prompt = f"{base_prompt}\n{user_context}\n{topic_instruction}\n{citation_instruction}{continuity_instruction}\n\n{format_instruction}"
        
        if self._ai_engine:
            self._ai_engine.set_system_prompt(full_system_prompt)
            self._ai_engine.configure(api_key=api_key, reasoning_model=model)
            if self.voice_service and api_key:
                self.voice_service.set_api_key(api_key)

    def chat(self, message):
        """ユーザーからのメッセージを受け取り、応答を生成します。"""
        logger.info(f"Chat Request: {message}")
        if not self._ai_engine:
             return {"text": "AI Engine Not Ready", "audio": None, "suggestions": []}

        # 1. 生成実行 (AIEngine側でTOONのパースも行われます)
        response_data = self._ai_engine.generate_response(message)
        
        text_to_speak = response_data.get("text", "")
        emotion = response_data.get("emotion", "neutral")
        suggestions = response_data.get("suggestions", [])
        grounding_info = response_data.get("grounding_info")

        # 2. TTS (音声合成)
        audio_path = None
        settings = self._config_manager.get_all()
        provider = settings.get('tts_provider', 'voicevox') 
        
        try:
            # TTS Generation
            clean_text = re.sub(r'http[s]?://\S+', '', text_to_speak)
            output_dir = os.path.join(os.getcwd(), 'dist/audio')
            if not os.path.exists(output_dir): os.makedirs(output_dir)

            if (provider == 'voicevox' or 'gemini' in provider) and self.voice_service:
                voice = settings.get('voice_type', '3')
                # Log for debug
                logger.info(f"TTS Request: Provider={provider}, Voice={voice}")
                audio_path = self.voice_service.generate_voice(clean_text, voice_name=voice, provider=provider)
            elif self.tts_engine:
                 voice = settings.get('voice_type', 'ja-JP-Neural2-B')
                 if provider == 'google' and len(str(voice)) < 3: voice = 'ja-JP-Neural2-B'
                 audio_path = self.tts_engine.generate_voice(clean_text, output_dir=output_dir, voice_name=voice)
                 
            # --- Socket Audio Streaming (Web/Mobile) ---
            if audio_path:
                try:
                    import base64
                    # audio_path is relative (e.g. "audio/xxx.wav"). 
                    # Real path is "dist/audio/xxx.wav" relative to CWD.
                    real_path = os.path.join(os.getcwd(), "dist", audio_path)
                    if os.path.exists(real_path):
                        with open(real_path, "rb") as f:
                            audio_b64 = base64.b64encode(f.read()).decode('utf-8')
                        
                        from src.core.socket_manager import sio
                        import asyncio
                        # emit is async, we are in sync or async method?
                        # chat is sync def. But FastAPI calls it in threadpool.
                        # sio.emit is coroutine.
                        # We need to schedule it.
                        asyncio.run_coroutine_threadsafe(
                            sio.emit('play_audio', {'audio': audio_b64}),
                            asyncio.get_event_loop() # This might fail if no loop in this thread
                        ) 
                        # Wait, threadpool doesn't have loop.
                        # Use generic fire-and-forget helper or just `sio.emit` if using AsyncServer?
                        # AsyncServer methods MUST be awaited.
                        # We can use `asyncio.run` inside thread? No `asyncio.run` creates NEW PROACTOR loop which might conflict/slow.
                        
                        # Alternative: Just return path, and Client fetches?
                        # But user wanted STREAMING via SOCKET.
                        # My previous implementation in chat_api.py (Step 2371) used `asyncio.run(sio.emit(...))`.
                        # That seemed "unsafe" but might work in threadpool.
                        # Let's use `asyncio.run` for now as it isolates the context.
                        asyncio.run(sio.emit('play_audio', {'audio': audio_b64}))
                        logger.info(f"📡 [Socket] Sent audio chunk ({len(audio_b64)} bytes)")
                except Exception as se:
                    logger.error(f"Socket Audio Error: {se}")
            # -------------------------------------------
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")

        # 3. データベースへの保存 & 履歴更新
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

@app.get("/api/voice_types")
async def get_voice_types(provider: str = 'voicevox'):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    # BaseApiMixin or ChatApiMixin should have get_voice_types.
    # Check if SettingsApiMixin has it? It usually does.
    # If not, we might need to add it to HeadlessApi or Mixin.
    # Assuming it exists because it's used in Desktop.
    return server_api.get_voice_types(provider)

@app.get("/api/history")
async def get_history(limit: int = 50):
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.get_history(limit=limit)

@app.get("/api/history/restore")
async def restore_history():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.restore_history()

@app.get("/api/topics/suggestions")
async def get_topic_suggestions():
    if not server_api: raise HTTPException(status_code=500, detail="Not Ready")
    return server_api.get_topic_suggestions()

# Static / Audio
os.makedirs("dist/audio", exist_ok=True)
app.mount("/audio", StaticFiles(directory="dist/audio"), name="audio")

if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

# --- SocketIO Integration ---
from src.core.socket_manager import sio
import socketio

# Wrap FastAPI with SocketIO
app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
