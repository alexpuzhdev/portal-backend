from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "portal-core"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://portal:portal@localhost:5432/portal",
        description="SQLAlchemy async DSN for the primary Postgres instance",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    rabbitmq_url: str = Field(default="amqp://portal:portal@localhost:5672/")

    s3_endpoint_url: str = Field(default="http://localhost:9000")
    s3_access_key: str = Field(default="portal")
    s3_secret_key: str = Field(default="portalpassword")
    s3_bucket: str = Field(default="portal")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
