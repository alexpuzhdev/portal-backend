# Модуль `auth`

Аутентификация (email + пароль), сессии (JWT в cookies), RBAC
(Casbin), модель пользователя и memberships.

См. [ADR-0010](../adr/0010-auth-jwt-cookies-casbin.md) — там
зафиксированы технические решения.

## Состав

- **Domain:** `User`, `Role`, `Membership`, `RefreshToken` entities;
  value objects `Email`, `HashedPassword`, `Permission`; password
  policy в `assert_password_policy`; exceptions
  (`InvalidCredentials`, `TokenExpired`, `TokenRevoked`,
  `WeakPassword`, etc.).
- **Application:**
  - Use cases: `CreateUser`, `Login`, `Logout`, `RefreshAccessToken`,
    `GetCurrentUser`.
  - Ports: `PasswordHasher`, `TokenIssuer`, `TokenDenylist`,
    `Enforcer`.
  - DTO: `LoginInput`, `TokensOutput`, `UserOutput`,
    `MembershipOutput`, `CurrentUserOutput`, `CreateUserInput`.
- **Infrastructure:**
  - ORM: `UserORM`, `RoleORM`, `PermissionORM`, `RolePermissionORM`,
    `UserOrganizationMembershipORM`, `RefreshTokenORM`.
  - Mappers, repositories.
  - Argon2 password hasher (`security/password_hasher.py`).
  - PyJWT-based `JwtTokenIssuer` (`security/token_issuer.py`).
  - Redis denylist (`security/token_denylist.py`).
  - `CasbinEnforcer` + `model.conf` (`casbin/`).
  - `bootstrap.py` — идемпотентное создание системных ролей и
    permissions.
- **Presentation:**
  - Routes: `POST /auth/login`, `POST /auth/logout`,
    `POST /auth/refresh`, `GET /auth/me`.
  - Cookies: `set_auth_cookies` / `clear_auth_cookies`.
  - DI: `current_user`, `current_organization`, `assert_csrf` —
    публичный API auth-модуля для других модулей.

## HTTP контракт

| Endpoint | Метод | Описание | Auth |
|----------|-------|----------|------|
| `/auth/login` | POST | email + password → ставит cookies, возвращает профиль + memberships | публичный |
| `/auth/logout` | POST | отзывает refresh, кладёт jti access в denylist, чистит cookies | требует cookies + CSRF |
| `/auth/refresh` | POST | rotation: новые access+refresh, старый refresh инвалидируется | требует cookies + CSRF |
| `/auth/me` | GET | профиль и memberships текущего пользователя | требует access cookie |

Cookies на login/refresh:

| Cookie | httpOnly | secure (prod) | TTL | Назначение |
|--------|----------|---------------|-----|------------|
| `portal_access` | да | да | 15 мин | JWT access |
| `portal_refresh` | да | да | 30 дней | JWT refresh |
| `portal_csrf` | **нет** | да | 30 дней | double-submit CSRF |

## Контекст организации

Контекст приходит из URL (`/portal/<orgSlug>/...`). Зависимость
`current_organization`:

1. Берёт `org_slug` из path-параметра.
2. Резолвит организацию по slug.
3. Проверяет, что пользователь имеет membership в этой организации.
4. Возвращает `organization_id` (UUID) для использования в роуте.

Если пользователь не имеет membership — 403 Forbidden.

## RBAC

Casbin enforcer с моделью «RBAC with domains». Permissions имеют
формат `<resource>:<action>`. Policy хранится в Postgres (та же БД).

Bootstrap-роли (в `infrastructure/bootstrap.py`):

| Роль | Permissions |
|------|-------------|
| `owner` | organizations:read, organizations:update, invitations:create, invitations:list, invitations:revoke, users:list, users:reset_password, memberships:create, memberships:remove |
| `admin` | то же без `organizations:update` |
| `member` | organizations:read |

В будущем (Этап 2+) роли и permissions станут настраиваемыми через UI.
Архитектура к этому готова — см. [project memory про Frappe-style RBAC](../../../portal-project/CLAUDE.md).

## Связь с другими модулями

- **Setup** (`setup` модуль) использует `CreateUser` + `bootstrap` +
  `Enforcer.add_role_for_user_in_organization` для инициализации
  инстанса.
- **Любой модуль с защищёнными эндпоинтами** импортирует
  `current_user` / `current_organization` / `assert_csrf` из
  `app.modules.auth.presentation.deps`.

## Архитектурный контракт

Контролируется `import-linter`:

- Слои `presentation → infrastructure → application → domain`.

## Что появится в следующих блоках

- **Блок 3 (tokens):** invitation flow и admin password reset, общая
  модель токенов (одна таблица `tokens` с дискриминатором).
- **Блок 4 (frontend):** страницы login / select-org / accept-invite /
  reset-password / settings.
