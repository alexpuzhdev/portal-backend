from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from ...domain.entities import User
from ...domain.exceptions import UserAlreadyExists
from ...domain.repositories import UserRepository
from ...domain.value_objects import Email, HashedPassword, assert_password_policy
from ..dto import CreateUserInput, UserOutput
from ..ports import PasswordHasher


@dataclass
class CreateUser:
    """Создаёт нового пользователя. Используется из /setup (первый
    owner) и из accept-invite (Блок 3). Валидирует password policy и
    уникальность email."""

    user_repository: UserRepository
    password_hasher: PasswordHasher

    async def execute(self, input_dto: CreateUserInput) -> UserOutput:
        email = Email(input_dto.email)
        if await self.user_repository.get_by_email(str(email)) is not None:
            raise UserAlreadyExists(str(email))

        assert_password_policy(input_dto.password)

        now = datetime.now()
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=HashedPassword(self.password_hasher.hash(input_dto.password)),
            full_name=input_dto.full_name.strip(),
            display_name=(
                input_dto.display_name.strip()
                if input_dto.display_name and input_dto.display_name.strip()
                else None
            ),
            phone=input_dto.phone.strip() if input_dto.phone and input_dto.phone.strip() else None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await self.user_repository.add(user)
        return UserOutput.from_entity(user)
