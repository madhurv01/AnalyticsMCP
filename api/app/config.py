from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-secret"
    env: str = "development"
    web_origin: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    google_client_id: str = ""
    google_client_secret: str = ""

    database_url: str = "postgresql+psycopg://insightforge:insightforge@localhost:5432/insightforge"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "insightforge"
    s3_region: str = "us-east-1"

    upload_max_bytes: int = 104_857_600
    inline_max_bytes: int = 5_242_880
    raw_rows_cap: int = 5_000

    session_cookie: str = "if_session"
    session_ttl_days: int = 7

    @property
    def is_prod(self) -> bool:
        return self.env == "production"

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.api_base_url}/api/auth/google/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
