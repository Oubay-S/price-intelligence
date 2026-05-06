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

    # Analyst-curated mart tables (dbt). Defaulted so deployments work
    # without overriding when the analyst follows the agreed naming.
    BIGQUERY_MART_PRODUCT_STATS: str  = "mart_product_stats"
    BIGQUERY_MART_BRAND_RANKINGS: str = "mart_brand_rankings"
    BIGQUERY_MART_PRICE_DROPS: str    = "mart_price_drops"
    BIGQUERY_MART_TRENDING: str       = "mart_trending"
    BIGQUERY_MART_SITE_PRICES: str    = "mart_site_prices"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Rate limits (slowapi syntax: "<count>/<period>"; e.g. "5/minute").
    # Overrides via .env let ops loosen them in dev or tighten in prod.
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"

    DATABASE_URL: str
    REDIS_URL: str
    NIFI_URL: str


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
