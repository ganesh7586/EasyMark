"""
Configuration settings for the AI Service using Pydantic Settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings schema with fail-fast validation."""

    PROJECT_NAME: str = "Company Intelligence AI Service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Critical security key shared with the Node.js Express Gateway
    INTERNAL_API_KEY: str = Field(
        ...,
        description="Shared secret key required in the x-internal-key header",
    )

    # Allowed CORS origins
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.ALLOWED_ORIGINS, str):
            import json
            try:
                return json.loads(self.ALLOWED_ORIGINS)
            except Exception:
                return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS


@lru_cache()
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()


settings = get_settings()
