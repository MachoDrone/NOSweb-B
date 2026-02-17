from fastapi import APIRouter, Request

from app.services.system_service import SystemService

router = APIRouter()


@router.get("/summary")
async def get_overview(request: Request):
    """Aggregated snapshot for the overview dashboard tab."""
    settings = request.app.state.settings
    docker_svc = request.app.state.docker_service
    gpu_svc = request.app.state.gpu_service

    system_stats = SystemService.get_system_stats()
    containers = docker_svc.list_all_containers()
    gpu_stats = gpu_svc.get_all_gpu_stats() if gpu_svc.enabled else []

    # If pynvml failed but GPU is supposed to be available, try nsenter
    if gpu_svc.enabled and not gpu_stats:
        gpu_stats = await gpu_svc.get_stats_via_nsenter()

    running = [c for c in containers if c["status"] == "running"]

    return {
        "system": system_stats,
        "containers": {
            "total": len(containers),
            "running": len(running),
            "list": containers,
        },
        "gpu": {
            "enabled": gpu_svc.enabled,
            "count": gpu_svc.device_count or len(gpu_stats),
            "devices": gpu_stats,
        },
    }
