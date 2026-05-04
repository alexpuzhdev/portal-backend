import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings

from ...application.ports import AccessTokenClaims, RefreshTokenClaims
from ...domain.exceptions import TokenExpired, TokenInvalid

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class JwtTokenIssuer:
    """PyJWT реализация TokenIssuer port. Симметричная подпись HS256
    по дефолту; в проде имеет смысл переключить на RS256, но это
    отдельное решение (отдельный ADR при необходимости)."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._access_ttl = timedelta(minutes=settings.access_token_ttl_minutes)
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)

    def issue_access(self, user_id: UUID) -> tuple[str, AccessTokenClaims]:
        return self._issue(user_id, ACCESS_TOKEN_TYPE, self._access_ttl)

    def issue_refresh(self, user_id: UUID) -> tuple[str, RefreshTokenClaims]:
        token, claims = self._issue(user_id, REFRESH_TOKEN_TYPE, self._refresh_ttl)
        return token, RefreshTokenClaims(
            jti=claims.jti,
            user_id=claims.user_id,
            issued_at=claims.issued_at,
            expires_at=claims.expires_at,
        )

    def decode_access(self, token: str) -> AccessTokenClaims:
        return self._decode(token, expected_type=ACCESS_TOKEN_TYPE)

    def decode_refresh(self, token: str) -> RefreshTokenClaims:
        claims = self._decode(token, expected_type=REFRESH_TOKEN_TYPE)
        return RefreshTokenClaims(
            jti=claims.jti,
            user_id=claims.user_id,
            issued_at=claims.issued_at,
            expires_at=claims.expires_at,
        )

    def hash_refresh(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _issue(
        self, user_id: UUID, token_type: str, ttl: timedelta
    ) -> tuple[str, AccessTokenClaims]:
        now = datetime.now(UTC)
        expires_at = now + ttl
        jti = secrets.token_urlsafe(24)
        payload = {
            "sub": str(user_id),
            "jti": jti,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, AccessTokenClaims(
            jti=jti,
            user_id=user_id,
            issued_at=now,
            expires_at=expires_at,
        )

    def _decode(self, token: str, expected_type: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpired from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalid from exc

        if payload.get("type") != expected_type:
            raise TokenInvalid

        try:
            user_id = UUID(payload["sub"])
            issued_at = datetime.fromtimestamp(payload["iat"], tz=UTC)
            expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        except (KeyError, ValueError) as exc:
            raise TokenInvalid from exc

        return AccessTokenClaims(
            jti=payload["jti"],
            user_id=user_id,
            issued_at=issued_at,
            expires_at=expires_at,
        )
