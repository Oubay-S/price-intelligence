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

    # Shared secret for the /internal/* endpoints (NiFi → FastAPI).
    # Empty string = dev mode, auth disabled. Set in .env to enforce.
    INTERNAL_API_KEY: str = ""

    # --- SMTP / email --------------------------------------------------
    # Dev/testing: Mailtrap (sandbox.smtp.mailtrap.io:587, STARTTLS).
    # Prod: Resend (smtp.resend.com:587, STARTTLS, username="resend",
    # password is the Resend API key).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True   # STARTTLS on a plaintext port (587)
    SMTP_USE_SSL: bool = False  # Implicit TLS on port 465; mutually exclusive with STARTTLS
    SMTP_TIMEOUT: int = 15      # seconds — socket connect/IO timeout

    EMAIL_FROM_ADDRESS: str = "no-reply@priceradar.local"
    EMAIL_FROM_NAME: str = "PriceRadar"

    # Public URL the frontend is served from. Used to build verification
    # and password-reset links that land in the user's inbox.
    FRONTEND_URL: str = "http://localhost:4200"

    # Token TTLs for the email flows (hours).
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    PASSWORD_RESET_TTL_HOURS: int = 1

    # ThreadPoolExecutor size for the non-blocking email sender.
    # SMTP is sync; 4 workers is enough for dev volume and lets a burst
    # of registrations / alerts overlap without blocking the event loop.
    EMAIL_THREAD_POOL_SIZE: int = 4

    # Master kill-switch — when False the email service no-ops every
    # send. Handy in CI / unit tests where there is no SMTP server.
    EMAIL_ENABLED: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
