from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MedGuard AI"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./medguard.db"
    storage_dir: Path = Path("storage/uploads")
    max_upload_mb: int = 25
    video_sample_every_n_frames: int = 3
    video_low_motion_threshold: float = 0.35
    video_abrupt_motion_threshold: float = 20.0
    video_max_frames: int = 900
    cors_origins: list[str] | str = ["http://localhost:8501"]
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_language_endpoint: str | None = None
    azure_language_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("video_sample_every_n_frames", "video_max_frames")
    @classmethod
    def positive_video_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Video processing limits must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

