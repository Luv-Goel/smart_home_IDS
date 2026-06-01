import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
)

class AppSettings(BaseModel):
    name: str = "Smart Home IDS"
    debug: bool = False
    log_level: str = "INFO"
    reload: bool = False

class DatabaseSettings(BaseModel):
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    password: Optional[str] = None # Will be populated from secrets

class MqttSettings(BaseModel):
    broker_url: str
    client_id: str
    keepalive: int = 60
    password: Optional[str] = None # Will be populated from secrets

class InferenceSettings(BaseModel):
    model_path: str
    device: str = "cpu"
    batch_size: int = 1
    num_threads: Optional[int] = None # For Edge optimizations

class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A simple settings source that loads variables from a YAML file
    at the project's root based on the APP_ENV variable.
    """

    def get_field_value(
        self, field: Field, field_name: str
    ) -> tuple[Any, str, bool]:
        env = os.environ.get("APP_ENV", "dev").lower()

        # Path resolution - assuming environments is in the same dir as this file
        base_dir = Path(__file__).parent
        yaml_file = base_dir / "environments" / f"{env}.yaml"

        if not yaml_file.exists():
            return None, field_name, False

        try:
            with open(yaml_file, "r") as f:
                file_content = yaml.safe_load(f)
        except Exception:
            return None, field_name, False

        if not file_content:
            return None, field_name, False

        field_value = file_content.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: Field, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}

        env = os.environ.get("APP_ENV", "dev").lower()
        base_dir = Path(__file__).parent
        yaml_file = base_dir / "environments" / f"{env}.yaml"

        if yaml_file.exists():
            with open(yaml_file, "r") as f:
                content = yaml.safe_load(f)
                if content:
                    d.update(content)
        return d


class Settings(BaseSettings):
    app: AppSettings
    database: DatabaseSettings
    mqtt: MqttSettings
    inference: InferenceSettings

    # Secrets mappings
    secret_key: Optional[str] = None
    database_password: Optional[str] = None
    mqtt_password: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        secrets_dir="/run/secrets" if os.path.exists("/run/secrets") else None, ignore_empty=True,  # Docker secrets support
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )

# Global settings instance
settings = Settings()

def reload() -> Settings:
    """
    Hot reload mechanism.
    Re-creates the settings instance to read from the files/env variables again.
    """
    global settings
    settings = Settings()
    return settings
