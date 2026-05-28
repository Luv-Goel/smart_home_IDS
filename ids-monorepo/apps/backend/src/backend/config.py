"""Backend-specific configuration for Smart Home IDS.

This module provides FastAPI-specific configuration and settings.
"""

from pydantic import Field

from ids_core.config import Settings


class BackendSettings(Settings):
    """Backend-specific settings."""

    # API settings
    api_title: str = Field(default="Smart Home IDS API")
    api_description: str = Field(default="IoT Intrusion Detection System API")
    api_version: str = Field(default="1.0.0")
    api_docs_enabled: bool = Field(default=True)

    # CORS settings
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])
    cors_credentials: bool = Field(default=True)
    cors_methods: list[str] = Field(default=["*"])
    cors_headers: list[str] = Field(default=["*"])

    # JWT settings
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expires: int = Field(default=900)  # 15 minutes
    jwt_refresh_token_expires: int = Field(default=86400)  # 24 hours

    # Session settings
    session_secret_key: str = Field(default="your-session-secret-key-change-in-production")

    # Database settings (override defaults)
    database_url: str = Field(default="postgresql+asyncpg://idsteam:password@localhost:5432/ids_backend")

    # WebSocket settings
    websocket_heartbeat_interval: int = Field(default=25)
    websocket_close_timeout: int = Field(default=60)

    # Rate limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)  # seconds

    # Logging settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_output: str = Field(default="stdout")