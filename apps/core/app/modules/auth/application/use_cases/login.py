from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from ...domain.entities import RefreshToken
from ...domain.exceptions import InactiveUser, InvalidCredentials
from ...domain.repositories import RefreshTokenRepository, UserRepository
from ...domain.value_objects import HashedPassword
from ..dto import LoginInput, TokensOutput
from ..ports import PasswordHasher, TokenIssuer


@dataclass
class Login:
    """Проверяет credentials, выпускает access + refresh токены.

    Намеренная защита от user-enumeration: для несуществующего email и
    для неверного пароля поднимается одно и то же InvalidCredentials.
    """

    user_repository: UserRepository
    refresh_token_repository: RefreshTokenRepository
    password_hasher: PasswordHasher
    token_issuer: TokenIssuer

    async def execute(self, input_dto: LoginInput) -> TokensOutput:
        user = await self.user_repository.get_by_email(input_dto.email)
        if user is None:
            raise InvalidCredentials

        if not self.password_hasher.verify(input_dto.password, str(user.hashed_password)):
            raise InvalidCredentials

        try:
            user.assert_can_login()
        except InactiveUser:
            raise

        # Прозрачный rehash: если параметры Argon2 сменились — пересчитываем.
        if self.password_hasher.needs_rehash(str(user.hashed_password)):
            user.change_password(HashedPassword(self.password_hasher.hash(input_dto.password)))

        now = datetime.now(UTC)
        user.mark_logged_in(now)
        await self.user_repository.update(user)

        access_token, access_claims = self.token_issuer.issue_access(user.id)
        refresh_token, refresh_claims = self.token_issuer.issue_refresh(user.id)

        await self.refresh_token_repository.add(
            RefreshToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=self.token_issuer.hash_refresh(refresh_token),
                issued_at=refresh_claims.issued_at,
                expires_at=refresh_claims.expires_at,
                user_agent=input_dto.user_agent,
                ip_address=input_dto.ip_address,
            )
        )

        return TokensOutput(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_claims.expires_at,
            refresh_expires_at=refresh_claims.expires_at,
            user_id=user.id,
        )
