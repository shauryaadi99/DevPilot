"""Application configuration management using Pydantic Settings."""

import json
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DevPilot application settings loaded from environment variables."""

    PROJECT_NAME: str = "DevPilot"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Workspace settings
    WORKSPACE_ROOT: str = "./workspaces"
    WORKSPACE_RETENTION_HOURS: int = 72

    # Database settings
    DATABASE_URL: str = "sqlite:///./devpilot.db"

    # Groq LLM settings
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TIMEOUT_SECONDS: float = 45.0

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


_settings_cache: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Return Settings instance, reloading from environment if reload=True."""
    global _settings_cache
    if reload or _settings_cache is None:
        _settings_cache = Settings()
    return _settings_cache
