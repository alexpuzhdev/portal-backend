from typing import Protocol


class TokenDenylist(Protocol):
    """Реestr отозванных access-token jti. Реализация — Redis в
    infrastructure/security/. Запись на каждый logout, чтение на
    каждой проверке access-токена."""

    async def add(self, jti: str, ttl_seconds: int) -> None: ...

    async def contains(self, jti: str) -> bool: ...
