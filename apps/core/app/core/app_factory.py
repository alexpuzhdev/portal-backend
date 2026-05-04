from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.modules.organizations.presentation.routes import router as organizations_router
from app.modules.setup.presentation.routes import router as setup_router

from .config import Settings, get_settings
from .logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(debug=settings.debug)
    logger = structlog.get_logger()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "core.startup",
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )
        yield
        logger.info("core.shutdown")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "version": settings.app_version}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(setup_router)
    app.include_router(organizations_router)

    return app
