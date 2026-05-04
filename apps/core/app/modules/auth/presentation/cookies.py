"""Хелперы для проставления и удаления auth-cookies. Изолируют все
детали (httpOnly / secure / samesite / TTL) в одном месте."""

import secrets
from datetime import datetime

from fastapi import Response

from app.core.config import Settings


def set_auth_cookies(
    response: Response,
    settings: Settings,
    access_token: str,
    refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> None:
    now = datetime.now(tz=access_expires_at.tzinfo)
    access_max_age = max(int((access_expires_at - now).total_seconds()), 0)
    refresh_max_age = max(int((refresh_expires_at - now).total_seconds()), 0)

    response.set_cookie(
        settings.access_cookie_name,
        access_token,
        max_age=access_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )

    # CSRF-токен — НЕ httpOnly: фронт его читает и кладёт в заголовок
    # X-CSRF-Token при мутациях. Срок жизни = refresh, обновляется при
    # каждом login/refresh.
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=refresh_max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    for name in (
        settings.access_cookie_name,
        settings.refresh_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(
            name,
            domain=settings.cookie_domain,
            path="/",
        )
