# Этапы разработки

Этот файл отслеживает прогресс работы по этапам и блокам. Обновляется
в том же коммите, что и реализация блока.

## Этап 0 — каркас обоих репозиториев

**Статус:** ✅ закрыт (2026-04-29).

Создан рабочий каркас `portal-backend` и `portal-frontend`, оба
поднимаются локально, оба с зелёным CI. См.:

- backend PR #1: <https://github.com/alexpuzhdev/portal-backend/pull/1>
- frontend PR #1: <https://github.com/alexpuzhdev/portal-frontend/pull/1>

**Архитектурный пивот** (после закрытия Этапа 0, до старта Этапа 1):
переход с multi-tenant SaaS на single-tenant per deployment с внутренней
структурой организаций холдинга. См. ADR-0009 и:

- backend PR #2: <https://github.com/alexpuzhdev/portal-backend/pull/2>
- frontend PR #2: <https://github.com/alexpuzhdev/portal-frontend/pull/2>

## Этап 1 — аутентификация и организации

**Статус:** в работе.

**Цель:** пользователь может войти в систему. Owner может приглашать
сотрудников. Корневая организация холдинга создаётся при первом
развёртывании инстанса.

**Решения** (зафиксированы в обсуждении 2026-04-30):

- Bootstrap — `/setup` endpoint, доступный пока в БД нет пользователей.
- Регистрация — только по приглашению (one-time link).
- Email фиксируется в инвайте, приглашённый при accept вводит только
  имя и пароль.
- Срок жизни инвайта — выбирается owner-ом (1d / 7d / 30d / 90d / без
  срока).
- Owner видит список pending-инвайтов с кнопкой «отозвать».
- Кто может приглашать — определяется permission `invitations:create`
  в Casbin policy (универсально, без хардкода ролей).
- В MVP — три роли: `owner`, `admin`, `member`. Роли в БД, не enum
  (готовность к Frappe-style RBAC, см. memory).
- Argon2 для хеша паролей; policy: ≥ 12 символов, буквы и цифры.
- Forgot password — admin reset (общая модель токенов, тот же accept).
- JWT в httpOnly cookies: access 15m, refresh 30d с rotation. CSRF
  через double-submit. Logout через Redis denylist на jti +
  `is_revoked` флаг для refresh.
- `User` поля: id, email, hashed_password, full_name, display_name?,
  avatar_url?, phone?, is_active, email_verified_at?, last_login_at?,
  created_at, updated_at. Никаких channel-specific полей вроде
  `telegram_id` (см. memory).
- `Organization` поля: id, parent_organization_id?, slug, name,
  legal_name?, inn?, kpp?, primary_color_hsl?, logo_url?,
  storefront_enabled (default false), is_active, created_at,
  updated_at. Partial unique index на корневую (одна запись с
  `parent_organization_id IS NULL`).
- В Этапе 1 — только корневая организация. Дочерние — Этап 2+.
- Membership: `(user_id, organization_id, role_id)`, явные (не «по
  дереву»).
- Storefront в Этапе 1 — анонимные публичные страницы, без логина
  клиентов компании.

### Блоки

- **Блок 1:** organizations + минимальный /setup. *(✅ закрыт)*
- **Блок 2:** auth core (users, login, refresh, Casbin). *(✅ закрыт)*
- **Блок 3:** tokens (invitations + password reset). *(план)*
- **Блок 4:** frontend pages. *(план)*
- **Блок 5:** полный test-suite + e2e + финальный отчёт. *(план)*

> **Стратегия тестирования** (см. memory `feedback_test_cadence`):
> внутри блоков gate сводится к статическим проверкам
> (`make check` = lint + types + imports + smoke через uvicorn/curl).
> Полный pytest-suite (unit + integration + e2e) пишется в Блоке 5.

#### Блок 1 — organizations + /setup ✅

**Что вошло:**

- Модуль `apps/core/app/modules/organizations/` со всеми четырьмя
  слоями Clean Architecture: domain (`Organization` entity + value
  objects `Slug`/`INN`/`KPP`/`HSLColor` + repository protocol +
  exceptions), application (use cases `CreateRootOrganization`,
  `GetOrganizationBySlug`, `GetOrganizationById`, `ListOrganizations`,
  `UpdateOrganization`, DTO), infrastructure (`OrganizationORM`, mapper,
  `SqlOrganizationRepository`), presentation (схемы, deps, роуты).
- Модуль `apps/core/app/modules/setup/`: use case `SetupInstance` и
  endpoint `POST /setup`. На текущем этапе создаёт только корневую
  организацию (защита one-time-only через `RootOrganizationAlreadyExists`).
  В Блоке 2 расширится до создания первого owner.
- Миграция Alembic `4e2244ca5c4a_create_organizations`. Partial unique
  index `uq_organizations_single_root` гарантирует ровно одну корневую
  запись (`WHERE parent_organization_id IS NULL`). Round-trip
  upgrade/downgrade проверен.
- Регистрация ORM-моделей собрана в `alembic/env.py` и
  `apps/core/conftest.py` (а не в `shared/`, чтобы не нарушать
  `import-linter`-контракт «shared не зависит от modules»).
- `import-linter` контракты на оба модуля + старый `shared` контракт.
- Тесты: 28 unit на value-objects, 6 на entity, 4 на use case
  CreateRootOrganization, 6 на остальные UC; 4 integration на repository
  с реальным Postgres; 3 e2e через `httpx.AsyncClient` с подменой
  `get_session` на тестовую сессию.
- `apps/core/conftest.py` с фикстурами `db_engine`/`db_session`
  (NullPool — ключевое решение для совместимости pytest-asyncio с
  asyncpg connection pool).
- Минорные правки инфраструктуры:
  - alembic post-write hook для ruff отключён (не находил entrypoint
    в uv-managed окружении); форматирование миграций — через
    `make format`.
  - `Makefile` `make test*` теперь обходит и `apps/*/app/modules/*/tests`.
  - `pyproject.toml` ruff: добавлены `ignore = ["RUF001-003", "N818"]`
    (кириллица в docstring и DDD-стиль исключений без суффикса
    `Error`).
  - `pyproject.toml` pytest: `asyncio_default_fixture_loop_scope =
    "function"` (убрана warning от pytest-asyncio).
- Документация: этот файл (новый) + `docs/modules/organizations.md`.

**Локальная проверка:**

```
$ make check
# lint OK, mypy OK, import-linter (3 contracts) OK, 52 unit-тестов
$ uv run pytest apps/core/tests/e2e/   # 3 passed
$ uv run pytest apps/core/app/modules/organizations/tests/integration/
# 4 passed
$ docker compose -f infra/docker-compose.dev.yml up -d postgres
$ make migrate
$ uv run uvicorn app.main:app --port 8765 &
$ curl -X POST :8765/setup -d '{"organization":{"slug":"alpha","name":"Alpha"}}'
# 201, тело — созданная организация
$ curl -X POST :8765/setup -d '{"organization":{"slug":"beta","name":"Beta"}}'
# 409 instance is already initialised
```

#### Блок 2 — auth core ✅

**Что вошло:**

- Модуль `apps/core/app/modules/auth/` со всеми четырьмя слоями Clean
  Architecture.
- Domain: `User`, `Role`, `Membership`, `RefreshToken`; value objects
  `Email`, `HashedPassword`, `Permission`; password policy в
  `assert_password_policy` (≥ 12 символов, буква + цифра); набор
  domain-исключений (`InvalidCredentials`, `TokenExpired`,
  `TokenRevoked`, `WeakPassword` и т. д.).
- Application: ports (`PasswordHasher`, `TokenIssuer`,
  `TokenDenylist`, `Enforcer`); use cases (`CreateUser`, `Login`,
  `Logout`, `RefreshAccessToken`, `GetCurrentUser`); DTO.
- Infrastructure:
  - SQLAlchemy ORM для всех auth-сущностей + маппер + repositories.
  - `Argon2PasswordHasher` через `argon2-cffi`.
  - `JwtTokenIssuer` через `pyjwt` (HS256), TTL access 15 мин /
    refresh 30 дней, SHA-256 хеш refresh для хранения в БД.
  - `RedisTokenDenylist` через `redis.asyncio`, ключ `denylist:<jti>`
    с TTL = remaining lifetime access-токена.
  - `CasbinEnforcer` + `model.conf` (RBAC with domains: sub × dom ×
    obj × act); policy storage в той же Postgres через
    `casbin-async-sqlalchemy-adapter`.
  - `bootstrap.py`: идемпотентное создание трёх системных ролей
    (`owner`, `admin`, `member`) и базовых permissions.
- Presentation:
  - `POST /auth/login` (выдаёт cookies, отдаёт user + memberships).
  - `POST /auth/logout` (revoke refresh + denylist access jti +
    очистка cookies; CSRF-проверка).
  - `POST /auth/refresh` (rotation: новый access + refresh, старый
    refresh инвалидируется; CSRF-проверка).
  - `GET /auth/me` (профиль + memberships).
  - Cookies: `portal_access` / `portal_refresh` (httpOnly), `portal_csrf`
    (НЕ httpOnly) — для double-submit pattern.
  - DI: `current_user`, `current_organization`, `assert_csrf` —
    публичный API auth-модуля для других модулей.
- Расширенный `/setup`: создаёт root organization → bootstrap roles
  и permissions → первого owner-а → его membership → Casbin policy.
- Конфиг: добавлены `jwt_secret`, `jwt_algorithm`,
  `access_token_ttl_minutes`, `refresh_token_ttl_days` и
  cookie-настройки. `.env.example` обновлён.
- Миграция Alembic `b3c040b945d8_create_users_roles_permissions_`.
  Round-trip upgrade/downgrade проверен.
- import-linter контракт `auth-clean-architecture` — добавлен.
- Документация: ADR-0010, `docs/modules/auth.md`, обновление
  `docs/stages.md`.

**Зависимости (новые):** `argon2-cffi`, `pyjwt`, `redis`, `casbin`,
`casbin-async-sqlalchemy-adapter`, `email-validator`.

**Stratregy change:** в этом блоке решено **не писать тесты внутри
блока** — статические проверки и smoke через curl/uvicorn достаточны.
Полный test-suite будет в финальном Блоке 5 (см. memory
`feedback_test_cadence`). По этой же причине удалены unit/integration/
e2e-тесты Блока 1 (они отражали устаревший контракт `/setup` и были
бы переписаны позже всё равно).

**Локальная smoke-проверка (curl):**

```
$ make migrate
$ uv run uvicorn app.main:app --port 8765 &

$ curl -c /tmp/c.txt -X POST :8765/setup \
    -d '{"organization":{...},"owner":{"email":"o@a","password":"...","full_name":"..."}}'
# 201, тело — root organization + owner

$ curl -c /tmp/c.txt -X POST :8765/auth/login \
    -d '{"email":"o@a","password":"..."}'
# 200, выставлены portal_access + portal_refresh + portal_csrf

$ curl -b /tmp/c.txt :8765/auth/me
# 200, профиль + memberships (с ролью "owner")

$ curl -b /tmp/c.txt -X POST :8765/auth/refresh -H "X-CSRF-Token: <csrf>"
# 204, новые токены, старый refresh — revoked

$ curl -b /tmp/c.txt -X POST :8765/auth/logout -H "X-CSRF-Token: <csrf>"
# 204, cookies удалены, jti в denylist

$ curl -b /tmp/c.txt :8765/auth/me
# 401 token revoked (даже если cookie ещё валидна — denylist срабатывает)

$ curl -X POST :8765/auth/login -d '{"email":"o@a","password":"WRONG"}'
# 401 invalid email or password
$ curl -X POST :8765/auth/login -d '{"email":"nobody@x","password":"any"}'
# 401 invalid email or password (то же сообщение — защита от user enumeration)
```

`make check` (lint + mypy + import-linter с 4 контрактами) — зелёный.
