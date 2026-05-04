from typing import Protocol


class PasswordHasher(Protocol):
    """Хеширование и проверка паролей. Реализация — Argon2 в
    infrastructure/security/."""

    def hash(self, raw_password: str) -> str: ...

    def verify(self, raw_password: str, hashed_password: str) -> bool: ...

    def needs_rehash(self, hashed_password: str) -> bool:
        """Проверяет, нужно ли перехешировать пароль (например, при
        изменении параметров Argon2). На каждом успешном login можно
        прозрачно обновить хеш."""
        ...
