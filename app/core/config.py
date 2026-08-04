from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="VIDEOMAKER_",
        extra="ignore",
    )

    app_name: str = "VideoMaker"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = Field(default="sqlite:///./videomaker.db")


@lru_cache
def get_settings() -> Settings:
    return Settings()
