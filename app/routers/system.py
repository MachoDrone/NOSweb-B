from fastapi import APIRouter

from app.services.system_service import SystemService

router = APIRouter()


@router.get("/stats")
async def get_system_stats():
    """Return host system stats (CPU, RAM, disk, uptime)."""
    return SystemService.get_system_stats()
