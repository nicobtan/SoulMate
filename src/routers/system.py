from fastapi import APIRouter
from pydantic import BaseModel
import logging

from src.core_instance import get_api

router = APIRouter(tags=["system"])
logger = logging.getLogger("router.system")

# --- Request Models ---
class LogRequest(BaseModel):
    message: str

# --- Endpoints ---

@router.post("/api/debug_log")
async def debug_log_endpoint(req: LogRequest):
    """Prints client-side logs to the server terminal."""
    # Just log it, no need for API instance really, but good practice
    logger.info(f"[CLIENT LOG] {req.message}")
    return {"status": "ok"}

@router.get("/api/calendar")
async def calendar_endpoint():
    api = get_api()
    if not hasattr(api, 'calendar_manager') or not api.calendar_manager:
        return {"events": []}
    
    # Mock authentication check
    if api.calendar_manager.is_authenticated:
        events = api.calendar_manager.get_upcoming_events()
        return {"events": events}
    return {"events": [], "error": "Not authenticated"}
