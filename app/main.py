from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.docker_service import DockerService
from app.services.gpu_service import GPUService
from app.routers import overview, system, gpu, docker_logs, commands


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown services."""
    app.state.settings = settings
    app.state.docker_service = DockerService(settings.DOCKER_SOCKET)
    app.state.gpu_service = GPUService(enabled=settings.HAS_GPU)
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

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("base.html", {
            "request": request,
            "has_gpu": settings.HAS_GPU,
        })

    return app


app = create_app()
