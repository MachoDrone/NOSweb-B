from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings, APP_VERSION
from app.services.docker_service import DockerService
from app.services.gpu_service import GPUService
from app.routers import overview, system, gpu, docker_logs, commands, update


async def _detect_gpu() -> bool:
    """Auto-detect NVIDIA GPU on host via nsenter nvidia-smi."""
    import asyncio
    try:
        proc = await asyncio.create_subprocess_exec(
            "nsenter", "-t", "1", "-m", "-u", "-i", "-n", "-p", "--",
            "nvidia-smi", "--query-gpu=name", "--format=csv,noheader",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        return proc.returncode == 0 and len(stdout.strip()) > 0
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown services."""
    app.state.settings = settings
    app.state.docker_service = DockerService(settings.DOCKER_SOCKET)

    # Auto-detect GPU if not explicitly set
    has_gpu = settings.HAS_GPU or await _detect_gpu()
    app.state.gpu_service = GPUService(enabled=has_gpu)

    yield
    app.state.docker_service.close()
    app.state.gpu_service.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nosana CoreLink",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Templates
    templates = Jinja2Templates(directory="app/templates")

    # Include API routers
    app.include_router(overview.router, prefix="/api/overview", tags=["overview"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])
    app.include_router(gpu.router, prefix="/api/gpu", tags=["gpu"])
    app.include_router(docker_logs.router, prefix="/api/logs", tags=["logs"])
    app.include_router(commands.router, prefix="/api/commands", tags=["commands"])
    app.include_router(update.router, prefix="/api/update", tags=["update"])

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("base.html", {
            "request": request,
            "has_gpu": settings.HAS_GPU,
            "app_version": APP_VERSION,
        })

    return app


app = create_app()
