from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.web_api.routers import camera, files, hsi, recording


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: inject CaptureService and HsiBuildService
    app.state.capture_service = None
    app.state.hsi_service = None
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="HSI Web API",
        version="0.1.0",
        description="API управления гиперспектральной системой съёмки",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(camera.router, prefix="/api/v1/camera", tags=["camera"])
    app.include_router(recording.router, prefix="/api/v1/recording", tags=["recording"])
    app.include_router(hsi.router, prefix="/api/v1/hsi", tags=["hsi"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
