import re
from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email

from .exceptions import WeakPassword


@dataclass(frozen=True)
class Email:
    """Email-адрес. Используется как уникальный идентификатор пользователя."""

    value: str

    def __post_init__(self) -> None:
        try:
            normalized = validate_email(self.value, check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError(f"invalid email '{self.value}': {exc}") from exc
        # Сохраняем нормализованный (lowercased domain) email
        object.__setattr__(self, "value", normalized.normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HashedPassword:
    """Контейнер для уже-захешированного пароля. Сам raw-пароль не
    хранится; хеширование делает PasswordHasher из application/ports."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("hashed password cannot be empty")

    def __str__(self) -> str:
        return self.value


# Минимальная длина пароля и требования к содержимому. Настройка
# зашита в код (не в env), потому что это инвариант продукта; если
# когда-нибудь понадобится конфиг — вынесем в Settings.
PASSWORD_MIN_LENGTH = 12


def assert_password_policy(raw_password: str) -> None:
    """Проверяет соответствие политике пароля: ≥ 12 символов, есть
    хотя бы одна буква и одна цифра. Бросает WeakPassword, если что
    не так."""
    if len(raw_password) < PASSWORD_MIN_LENGTH:
        raise WeakPassword(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Za-zА-Яа-яЁё]", raw_password):
        raise WeakPassword("password must contain at least one letter")
    if not re.search(r"\d", raw_password):
        raise WeakPassword("password must contain at least one digit")


@dataclass(frozen=True)
class Permission:
    """Имя permission'а в формате `<resource>:<action>` плюс уровень
    (level) — последний на старте всегда 0, зарезервирован под
    Frappe-style permission levels (см. project memory)."""

    resource: str
    action: str
    level: int = 0

    _NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    def __post_init__(self) -> None:
        if not self._NAME_PATTERN.fullmatch(self.resource):
            raise ValueError(f"invalid permission resource '{self.resource}'")
        if not self._NAME_PATTERN.fullmatch(self.action):
            raise ValueError(f"invalid permission action '{self.action}'")
        if self.level < 0:
            raise ValueError("permission level must be >= 0")

    @property
    def code(self) -> str:
        return f"{self.resource}:{self.action}"

    def __str__(self) -> str:
        return self.code
