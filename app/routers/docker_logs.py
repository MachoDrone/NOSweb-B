import asyncio
from concurrent.futures import ThreadPoolExecutor

from docker.errors import NotFound, APIError
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

router = APIRouter()

# Thread pool for blocking Docker SDK log reads
_executor = ThreadPoolExecutor(max_workers=4)


@router.get("/containers")
async def list_containers(request: Request):
    """List all Docker containers (for the log viewer dropdown)."""
    docker_svc = request.app.state.docker_service
    return docker_svc.list_all_containers()


@router.websocket("/ws/{container_id}")
async def stream_container_logs(
    websocket: WebSocket, container_id: str
):
    """Stream live logs from a Docker container via WebSocket."""
    await websocket.accept()
    docker_svc = websocket.app.state.docker_service

    try:
        log_stream = docker_svc.stream_logs(container_id, tail=200)
    except NotFound:
        await websocket.send_json({
            "type": "error",
            "data": f"Container '{container_id}' not found.",
        })
        await websocket.close()
        return
    except APIError as e:
        await websocket.send_json({
            "type": "error",
            "data": f"Docker error for '{container_id}': {e.explanation or str(e)}",
        })
        await websocket.close()
        return

    if log_stream is None:
        await websocket.send_json({
            "type": "error",
            "data": "Docker service is not available.",
        })
        await websocket.close()
        return

    loop = asyncio.get_event_loop()

    try:
        # Read from the blocking Docker log generator in a thread
        queue = asyncio.Queue(maxsize=100)

        def _read_logs():
            """Blocking reader that buffers chunks into lines."""
            try:
                buffer = ""
                for chunk in log_stream:
                    decoded = chunk.decode("utf-8", errors="replace")
                    buffer += decoded
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        asyncio.run_coroutine_threadsafe(
                            queue.put(line + "\n"), loop
                        )
                # Flush remaining buffer
                if buffer:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(buffer), loop
                    )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"__error__": str(e)}), loop
                )
            finally:
                asyncio.run_coroutine_threadsafe(
                    queue.put(None), loop
                )

        # Start blocking reader in thread
        future = loop.run_in_executor(_executor, _read_logs)

        # Send log lines from the async queue
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, dict) and "__error__" in item:
                await websocket.send_json({
                    "type": "error",
                    "container": container_id,
                    "data": f"Log stream interrupted: {item['__error__']}",
                })
                break
            await websocket.send_json({
                "type": "log_line",
                "container": container_id,
                "data": item,
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
            await websocket.close()
        except Exception:
            pass
