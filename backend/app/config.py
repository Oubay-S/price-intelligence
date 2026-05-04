from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    GCP_PROJECT_ID: str
    BIGQUERY_DATASET: str
    BIGQUERY_TABLE: str
    GOOGLE_APPLICATION_CREDENTIALS: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str
    REDIS_URL: str
    NIFI_URL: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
