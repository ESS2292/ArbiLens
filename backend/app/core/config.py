from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="ArbiLens API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret_key: str = Field(default="development-secret-key", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, alias="MAX_UPLOAD_SIZE_BYTES")
    app_base_url: str = Field(default="http://localhost:3000", alias="APP_BASE_URL")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/arbilens",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://redis:6379/1",
        alias="CELERY_RESULT_BACKEND",
    )

    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="arbilens-documents", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_timeout_seconds: int = Field(default=30, alias="OPENAI_TIMEOUT_SECONDS")
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_temperature: float = Field(default=0.0, alias="OPENAI_TEMPERATURE")
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id: str = Field(default="", alias="STRIPE_PRICE_ID")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
