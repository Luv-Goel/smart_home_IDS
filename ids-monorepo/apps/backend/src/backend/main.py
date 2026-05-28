"""Main FastAPI application for Smart Home IDS.

This module creates and configures the main application.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn.config import Config

from ids_core.config import Settings, get_settings
from ids_core.logger import setup_logging, get_logger

from backend.routers import alerts, devices, auth, health


logger = get_logger("backend.main")


def create_middleware(settings: Settings) -> list[Middleware]:
    """Create middleware list.

    Args:
        settings: Settings instance

    Returns:
        List of middleware
    """
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_credentials,
            allow_methods=settings.cors_methods,
            allow_headers=settings.cors_headers,
        ),
    ]

    return middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        settings: Settings instance (optional)

    Returns:
        FastAPI application
    """
    settings = settings or get_settings()
    setup_logging()

    middleware = create_middleware(settings)

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
        middleware=middleware,
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(alerts.router)
    app.include_router(devices.router)
    app.include_router(auth.router)
    app.include_router(health.router)

    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Global exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Args:
        app: FastAPI application

    Yields:
        None
    """
    logger.info("Starting backend application")

    # Startup tasks
    awaitstartup(app)

    yield

    # Shutdown tasks
    await shutdown(app)

    logger.info("Backend application stopped")


async def startup(app: FastAPI) -> None:
    """Startup tasks.

    Args:
        app: FastAPI application
    """
    logger.info("Running startup tasks")


async def shutdown(app: FastAPI) -> None:
    """Shutdown tasks.

    Args:
        app: FastAPI application
    """
    logger.info("Running shutdown tasks")


def get_settings() -> Settings:
    """Get settings.

    Returns:
        Settings instance
    """
    return get_settings()


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    config = Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
    uvicorn.Server(config).run()