from dataclasses import dataclass
from datetime import UTC, datetime

from ...domain.repositories import RefreshTokenRepository
from ..ports import TokenDenylist, TokenIssuer


@dataclass
class Logout:
    """Logout: помечает refresh-токен (если есть) как revoked в БД и
    кладёт jti access-токена (если ещё валиден) в denylist на остаток
    его TTL. Вызывающий слой потом обнулит cookie на клиенте."""

    refresh_token_repository: RefreshTokenRepository
    token_issuer: TokenIssuer
    denylist: TokenDenylist

    async def execute(self, access_token: str | None, refresh_token: str | None) -> None:
        if refresh_token is not None:
            token_hash = self.token_issuer.hash_refresh(refresh_token)
            record = await self.refresh_token_repository.get_by_hash(token_hash)
            if record is not None and not record.is_revoked:
                record.revoke()
                await self.refresh_token_repository.update(record)

        if access_token is not None:
            try:
                claims = self.token_issuer.decode_access(access_token)
            except Exception:
                # Невалидный access — нечего denylist'ить.
                return
            ttl = (claims.expires_at - datetime.now(UTC)).total_seconds()
            if ttl > 0:
                await self.denylist.add(claims.jti, int(ttl))
