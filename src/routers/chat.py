from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging

from src import core_instance

# Service Locator pattern for simple access
def get_db():
    return core_instance.get_db()

router = APIRouter(tags=["chat"])
logger = logging.getLogger("router.chat")

# --- Models ---
class ChatRequest(BaseModel):
    text: str
    session_id: Optional[int] = None # 既存セッションの続きならIDを指定

class ChatResponse(BaseModel):
    response: str
    audio: Optional[str] = None
    suggestions: List[str] = []
    session_id: int # クライアントに現在のセッションIDを返す

# --- Endpoints ---

@router.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    db = get_db()
    
    # 1. セッションの特定 (IDがなければ新規作成、あればその続き)
    session_id = req.session_id
    if not session_id:
        active = db.get_active_session()
        if active:
            session_id = active['id']
        else:
            session_id = db.create_session()
    
    # 2. ユーザーの入力を保存
    db.add_message(session_id, "user", req.text)
    
    # 3. AI生成
    api = core_instance.get_api()
    ai_response_obj = await api.chat(req.text) 
    
    # 4. AIの応答を保存 (★修正: meta情報としてsuggestionsを保存)
    ai_text = ai_response_obj.get("response") or ai_response_obj.get("text")
    suggestions = ai_response_obj.get("suggestions", [])
    
    if ai_text:
        meta = {"suggestions": suggestions} # メタデータ作成
        db.add_message(session_id, "ai", ai_text, meta=meta)
        
    # Process Audio Path -> URL (Duplicate logic from refactor, but kept for safety)
    if ai_response_obj.get('audio'):
        abs_path = ai_response_obj['audio']
        filename = os.path.basename(abs_path)
        ai_response_obj['audio'] = f"/audio/{filename}"

    # 5. レスポンス返却
    return {
        "response": ai_text,
        "audio": ai_response_obj.get("audio"),
        "suggestions": ai_response_obj.get("suggestions", []),
        "session_id": session_id,
        "grounding_info": ai_response_obj.get("grounding_info")
    }

# ... force_talk ...

@router.post("/api/history/{session_id}/resume")
async def resume_session(session_id: int):
    """
    特定の過去会話を「現在の会話」として再開し、復元用データを返す。
    """
    db = get_db()
    
    # 1. 存在確認
    messages = db.get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. DB上でタイムスタンプ更新（最新のセッションにする）
    db.update_session_timestamp(session_id)
    
    # 3. 最後のAIメッセージからサジェストを取得
    last_suggestions = []
    # 後ろから探索してAIの発言を探す
    for msg in reversed(messages):
        if msg['role'] == 'ai':
            # msg is sqlite3.Row object, access by key if configured, or index? 
            # DatabaseManager uses sqlite3.Row.
            # meta_json column needs parsing. 
            # DANGER: db.get_messages likely returns objects with 'meta_json' string.
            # We need to parse it safely.
            try:
                import json
                meta_json = msg['meta_json']
                if meta_json:
                    meta = json.loads(meta_json)
                    if meta and 'suggestions' in meta:
                        last_suggestions = meta['suggestions']
                        break
            except:
                pass
            
    # API互換性のため、RowオブジェクトをDictに変換
    messages_list = [dict(m) for m in messages]

    # 4. 復元用データを返す
    return {
        "status": "resumed",
        "session_id": session_id,
        "messages": messages_list,
        "suggestions": last_suggestions
    }

@router.post("/api/force_talk")
async def force_talk_endpoint():
    """Triggers a proactive message from the AI."""
    api = core_instance.get_api()
    logger.info("[Force Talk] Triggered via API")

    if hasattr(api, 'force_talk'):
        # Force Talk logic usually initiates a new thought, might not fit into a strict session if random?
        # But we should probably log it to the active session too.
        # For now, just call API. The API's chat() calls history_manager, 
        # but we want DB.
        # Ideally force_talk should accept a session_id or handle it.
        # Since force_talk calls self.chat(prompt), and self.chat is NOT the endpoint above but HeadlessApi.chat...
        # We need to hook into HeadlessApi to use DB? 
        # OR HeadlessApi.chat needs to be updated to use DB?
        # Ideally HeadlessApi should use DBManager instead of HistoryManager.
        # For now, let's just return. The internal call to `self.chat` in HeadlessApi is what generates text.
        # But HeadlessApi.chat doesn't know about `db` unless we inject it.
        # User goal is to save history.
        # If HeadlessApi.chat is called, it returns dict.
        # We should capture that return value here and save to DB?
        # But force_talk calls self.chat internally.
        # Allow existing force_talk to run, but we can't capture the text easily unless force_talk returns it.
        # It does return it.
        
        resp = api.force_talk()
        
        # Save to DB if possible
        db = get_db()
        active = db.get_active_session()
        if active:
            # We don't have the "prompt" (it was internal), but we have the AI response.
            if resp.get("text"):
                db.add_message(active['id'], "ai", resp.get("text"))
        
        return resp
    else:
        return {"text": "Error: force_talk not implemented", "audio": None}

@router.get("/api/history")
async def get_history_endpoint(limit: int = 50):
    """Old JSON history (Deprecated but kept for compat)."""
    # Prefer DB history
    try:
        db = get_db()
        # Get flattened messages from active session?
        # Or just return JSON format from DB?
        active = db.get_active_session()
        if active:
            msgs = db.get_messages(active['id'], limit)
            # Format for frontend
            return [{"role": m["role"], "content": m["content"]} for m in msgs]
    except:
        pass
    
    api = core_instance.get_api()
    if hasattr(api, 'get_history'):
         return api.get_history(limit=limit)
    return []

@router.get("/api/history/sessions")
async def get_sessions():
    """過去の会話リストを取得"""
    db = get_db()
    return db.get_sessions(limit=50)

@router.get("/api/history/{session_id}")
async def get_session_messages(session_id: int):
    """特定の会話の中身を取得"""
    db = get_db()
    messages = db.get_messages(session_id)
    return {"id": session_id, "messages": messages}

@router.post("/api/history/{session_id}/resume")
async def resume_session(session_id: int):
    """
    特定の過去会話を「現在の会話」として再開する。
    """
    db = get_db()
    messages = db.get_messages(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # DB上でタイムスタンプ更新（最新のセッションにする）
    db.update_session_timestamp(session_id)
    
    # AIエンジンのコンテキストをリセットしてロード (Future Work)
    # api = core_instance.get_api()
    # pass 

    return {"status": "resumed", "session_id": session_id}
