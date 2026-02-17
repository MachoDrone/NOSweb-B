from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

from app.services.command_service import CommandService, PRESET_COMMANDS

router = APIRouter()


@router.get("/presets")
async def get_preset_commands():
    """Return the catalog of pre-written commands for button UI."""
    return PRESET_COMMANDS


@router.websocket("/ws/exec")
async def execute_command_ws(websocket: WebSocket):
    """Execute a command on the host and stream output via WebSocket."""
    await websocket.accept()
    settings = websocket.app.state.settings

    cmd_service = CommandService(
        allowed_prefixes=settings.ALLOWED_COMMAND_PREFIXES,
        allow_custom=settings.ALLOW_CUSTOM_COMMANDS,
        timeout=settings.COMMAND_TIMEOUT,
    )

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command", "").strip()

            if not command:
                await websocket.send_json({
                    "type": "exec_error",
                    "data": "Empty command",
                })
                continue

            await websocket.send_json({
                "type": "exec_start",
                "command": command,
            })

            async for line in cmd_service.run_command(command):
                await websocket.send_json({
                    "type": "exec_output",
                    "data": line,
                })

            await websocket.send_json({
                "type": "exec_done",
                "command": command,
            })

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
