class UserNotFound(Exception):
    pass


class UserAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    """Email или пароль не совпадают. Намеренно одно сообщение для
    обоих случаев — не выдаём, существует ли email."""


class InactiveUser(Exception):
    pass


class TokenInvalid(Exception):
    """Подпись/формат токена не валидны или токен испорчен."""


class TokenExpired(Exception):
    pass


class TokenRevoked(Exception):
    """Refresh-токен отозван (logout) или access-токен в denylist."""


class RoleNotFound(Exception):
    pass


class MembershipNotFound(Exception):
    pass


class PermissionDenied(Exception):
    """RBAC отказал в доступе к ресурсу/действию."""


class WeakPassword(Exception):
    """Пароль не проходит policy: ≥ 12 символов, буквы и цифры."""
