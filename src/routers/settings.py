from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List
import logging

from src.core_instance import get_api

router = APIRouter(tags=["settings"])
logger = logging.getLogger("router.settings")

# --- Request Models ---
class ChangePersonaRequest(BaseModel):
    persona_id: str

# --- Endpoints ---

@router.get("/api/settings")
async def settings_endpoint():
    """Returns current server configuration."""
    api = get_api()
    return api.config_manager.get_all()

@router.post("/api/settings")
async def save_settings_endpoint(settings: Dict[str, Any]):
    """Updates server configuration."""
    api = get_api()
    
    # Update ConfigManager
    api.config_manager.config.update(settings)
    api.config_manager.save()
    
    # Re-configure AI (Important for API Key)
    api._configure_ai(api.config_manager.config)
    
    # Push to Bubble Service if exists
    if hasattr(api, 'bubble_service') and api.bubble_service:
        api.bubble_service.update_settings(api.config_manager.config)
    
    return {"status": "ok", "config": api.config_manager.get_all()}

@router.get("/api/personas")
async def get_personas_endpoint():
    """Returns list of available personas."""
    api = get_api()
    return api.get_persona_list()

@router.post("/api/persona/change")
async def change_persona_endpoint(req: ChangePersonaRequest):
    """Switches the current persona."""
    api = get_api()
    
    result = api.change_persona(req.persona_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    
    return result
