from fastapi import APIRouter

from app.config import APP_VERSION
from app.services.update_service import trigger_update, get_update_status

router = APIRouter()


@router.post("/apply")
async def apply_update():
    """Trigger a self-update: download latest source, rebuild, restart."""
    return await trigger_update()


@router.get("/status")
async def update_status():
    """Read the host-side update log to check progress."""
    return await get_update_status()


@router.get("/version")
async def current_version():
    """Return current running version (used by frontend after reconnect)."""
    return {"version": APP_VERSION}
