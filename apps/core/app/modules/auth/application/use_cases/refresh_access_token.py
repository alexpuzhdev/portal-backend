from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from ...domain.entities import RefreshToken
from ...domain.exceptions import (
    InactiveUser,
    TokenExpired,
    TokenInvalid,
    TokenRevoked,
    UserNotFound,
)
from ...domain.repositories import RefreshTokenRepository, UserRepository
from ..dto import TokensOutput
from ..ports import TokenIssuer


@dataclass
class RefreshAccessToken:
    """Вращение refresh-токена с rotation: старый инвалидируется,
    выпускается новая пара (access + refresh).

    Защита от replay: если приходит уже-revoked токен, **отзываем все**
    refresh-токены пользователя (фрод-сигнал, кто-то использует
    украденный refresh).
    """

    user_repository: UserRepository
    refresh_token_repository: RefreshTokenRepository
    token_issuer: TokenIssuer

    async def execute(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokensOutput:
        try:
            claims = self.token_issuer.decode_refresh(refresh_token)
        except TokenExpired:
            raise
        except Exception as exc:
            raise TokenInvalid from exc

        token_hash = self.token_issuer.hash_refresh(refresh_token)
        record = await self.refresh_token_repository.get_by_hash(token_hash)
        if record is None:
            raise TokenInvalid

        if record.is_revoked:
            # Подозрение на компрометацию — обнуляем все refresh-токены
            # пользователя. Любая активная сессия будет вынуждена
            # перелогиниться.
            await self.refresh_token_repository.revoke_all_for_user(record.user_id)
            raise TokenRevoked

        if record.expires_at <= datetime.now(UTC):
            raise TokenExpired

        user = await self.user_repository.get_by_id(record.user_id)
        if user is None:
            raise UserNotFound
        try:
            user.assert_can_login()
        except InactiveUser:
            raise

        # Rotation: новые токены, старый помечается revoked + replaced_by.
        new_access, access_claims = self.token_issuer.issue_access(user.id)
        new_refresh, refresh_claims = self.token_issuer.issue_refresh(user.id)
        new_record_id = uuid4()
        await self.refresh_token_repository.add(
            RefreshToken(
                id=new_record_id,
                user_id=user.id,
                token_hash=self.token_issuer.hash_refresh(new_refresh),
                issued_at=refresh_claims.issued_at,
                expires_at=refresh_claims.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        record.revoke(replaced_by_id=new_record_id)
        await self.refresh_token_repository.update(record)

        # Игнорируем claims.user_id — для совместимости проверяем по
        # record.user_id (он точно соответствует тому, что в БД).
        _ = claims

        return TokensOutput(
            access_token=new_access,
            refresh_token=new_refresh,
            access_expires_at=access_claims.expires_at,
            refresh_expires_at=refresh_claims.expires_at,
            user_id=user.id,
        )
