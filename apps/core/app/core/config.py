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

    # JWT и cookie auth (см. ADR-0010).
    # JWT_SECRET обязателен в production — дефолт ниже работает только
    # для разработки и тестов; запуск с этим секретом в проде должен
    # отклоняться (см. validation в Settings.__init__ при необходимости).
    jwt_secret: str = Field(
        default="dev-only-secret-change-me",
        description="HMAC secret for signing JWT tokens",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_minutes: int = Field(default=15, ge=1)
    refresh_token_ttl_days: int = Field(default=30, ge=1)

    # Cookie-настройки. На локалке и в тестах — http (secure=false).
    # Прод-окружение должно переопределять через .env (secure=true,
    # samesite=lax/strict, домен).
    cookie_secure: bool = Field(default=False)
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax")
    cookie_domain: str | None = Field(default=None)
    access_cookie_name: str = Field(default="portal_access")
    refresh_cookie_name: str = Field(default="portal_refresh")
    csrf_cookie_name: str = Field(default="portal_csrf")
    csrf_header_name: str = Field(default="X-CSRF-Token")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
