"""Configuration management for Smart Home IDS.

This module provides Pydantic-based configuration loading with environment
variables, YAML support, and validation.
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import (
    BaseModel,
    BaseSettings,
    Field,
    post_init,
    field_validator,
    ConfigDict,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class Settings(BaseSettings):
    """Main settings for Smart Home IDS.

    Loads configuration from environment variables and YAML files.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_prefix="",
    )

    # Application settings
    app_name: str = "Smart Home IDS"
    app_version: str = "0.1.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Logging settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_output: str = Field(default="stdout")

    # Database settings
    database_url: str = Field(default="postgresql+asyncpg://idsteam:password@localhost:5432/ids")
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379/0")

    # MQTT settings
    mqtt_broker_url: str = Field(default="mqtt://localhost:1883")
    mqtt_client_id: str = Field(default="ids-client")
    mqtt_keepalive: int = Field(default=60)
    mqtt_clean_session: bool = Field(default=True)

    # Edge settings
    node_id: str = Field(default="edge-node-01")
    network_interface: str = Field(default="eth0")

    # ML settings
    ml_model_path: str = Field(default="models/rf_lightweight_v1.onnx")
    ml_batch_size: int = Field(default=32)
    ml_confidence_threshold: float = Field(default=0.75)

    # API settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: list = Field(default=["*"])

    @classmethod
    def settings_customise_sources(
        cls,
        settings: BaseSettings,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize source order to load YAML first, then override with env."""
        yaml_file = Path("config.yaml")
        if yaml_file.exists():
            return (init_settings, YamlConfigSettingsSource(settings, yaml_file), env_settings, dotenv_settings, file_secret_settings)
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper_v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


class DatabaseConfig(BaseModel):
    """Database-specific configuration."""

    url: str = Field(default_factory=lambda: settings.database_url)
    pool_size: int = Field(default=settings.database_pool_size)
    max_overflow: int = Field(default=settings.database_max_overflow)

    @property
    def async_url(self) -> str:
        """Return async database URL."""
        if "+asyncpg" not in self.url:
            return self.url.replace("postgresql://", "postgresql+asyncpg://")
        return self.url


class MQTTConfig(BaseModel):
    """MQTT-specific configuration."""

    broker_url: str = Field(default=settings.mqtt_broker_url)
    client_id: str = Field(default=settings.mqtt_client_id)
    keepalive: int = Field(default=settings.mqtt_keepalive)
    clean_session: bool = Field(default=settings.mqtt_clean_session)


class LogConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default=settings.log_level)
    format: str = Field(default=settings.log_format)
    output: str = Field(default=settings.log_output)