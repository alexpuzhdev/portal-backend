from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class Argon2PasswordHasher:
    """Argon2 реализация PasswordHasher port. Параметры по умолчанию
    argon2-cffi разумны для 2026 года; при необходимости можно
    настроить через конструктор."""

    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash(self, raw_password: str) -> str:
        return self._hasher.hash(raw_password)

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        try:
            self._hasher.verify(hashed_password, raw_password)
        except (VerifyMismatchError, InvalidHashError):
            return False
        return True

    def needs_rehash(self, hashed_password: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(hashed_password)
        except InvalidHashError:
            # Если хеш сломан — лучше «нужен rehash», чтобы Login
            # пересчитал его при следующем успешном вводе пароля.
            return True
