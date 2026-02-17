import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

router = APIRouter()


@router.get("/stats")
async def get_gpu_stats(request: Request):
    """Return a snapshot of all GPU stats."""
    gpu_svc = request.app.state.gpu_service

    stats = gpu_svc.get_all_gpu_stats()

    # Fallback to nsenter nvidia-smi if pynvml is not working
    if gpu_svc.enabled and not stats:
        stats = await gpu_svc.get_stats_via_nsenter()

    return {
        "enabled": gpu_svc.enabled,
        "device_count": gpu_svc.device_count or len(stats),
        "devices": stats,
    }


@router.websocket("/ws")
async def gpu_stats_ws(websocket: WebSocket):
    """Stream GPU stats every 2 seconds via WebSocket."""
    await websocket.accept()
    gpu_svc = websocket.app.state.gpu_service

    try:
        while True:
            stats = gpu_svc.get_all_gpu_stats()

            if gpu_svc.enabled and not stats:
                stats = await gpu_svc.get_stats_via_nsenter()

            await websocket.send_json({
                "type": "gpu_stats",
                "data": stats,
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
