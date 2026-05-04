from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AccessTokenClaims:
    jti: str
    user_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class RefreshTokenClaims:
    jti: str
    user_id: UUID
    issued_at: datetime
    expires_at: datetime


class TokenIssuer(Protocol):
    """Выпуск и валидация JWT-токенов. Реализация — pyjwt в
    infrastructure/security/."""

    def issue_access(self, user_id: UUID) -> tuple[str, AccessTokenClaims]: ...

    def issue_refresh(self, user_id: UUID) -> tuple[str, RefreshTokenClaims]: ...

    def decode_access(self, token: str) -> AccessTokenClaims: ...

    def decode_refresh(self, token: str) -> RefreshTokenClaims: ...

    def hash_refresh(self, token: str) -> str:
        """Хеш refresh-токена для хранения в БД (нельзя хранить в plain
        — компрометация БД давала бы доступ ко всем сессиям)."""
        ...
