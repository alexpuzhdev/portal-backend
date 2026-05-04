# 0010. Auth: JWT в httpOnly cookies + Casbin policy в БД

Дата: 2026-05-04
Статус: принято

## Контекст

Этап 1 вводит аутентификацию и авторизацию. Нужно зафиксировать
ключевые технические решения, чтобы они не переоткрывались по ходу
разработки модулей и оставались согласованы между бэкендом и фронтом.

Контекст продукта (см. ADR-0009): один деплой Portal обслуживает один
клиент-холдинг, внутри — дерево организаций. Пользователь может иметь
membership к нескольким организациям внутри инстанса; конкретная
организация выбирается через URL (`/portal/<orgSlug>/...`).

## Решения

### Глобальный login + URL-driven контекст организации

`POST /auth/login` принимает email + password и выдаёт пару токенов
**без** `organization_id` в payload. Контекст организации определяется
из path-параметра роута (`/portal/<orgSlug>/...`); FastAPI Depends
`current_organization` извлекает slug, проверяет membership текущего
пользователя и кладёт `organization_id` в запрос.

Преимущества: переключение между организациями не требует выпуска
новых токенов; токен валиден для всех memberships пользователя.

### JWT в httpOnly cookies + double-submit CSRF

- **Access** — JWT в httpOnly cookie `portal_access`, TTL 15 минут.
- **Refresh** — JWT в httpOnly cookie `portal_refresh`, TTL 30 дней.
- **CSRF** — случайный токен в cookie `portal_csrf` (НЕ httpOnly), TTL
  совпадает с refresh. Фронт читает его и отправляет в заголовке
  `X-CSRF-Token` на каждой мутации (`POST/PUT/PATCH/DELETE`). Бэкенд
  через зависимость `assert_csrf` сравнивает cookie и заголовок.
- В dev: `cookie_secure=false`, в prod: `secure=true` через `.env`.

Хранение в httpOnly защищает от XSS (фронт не имеет доступа к токенам
из JavaScript); double-submit CSRF защищает от CSRF при отсутствии
SameSite-strict.

### Refresh с rotation + Redis denylist на access jti

- **Refresh rotation:** при каждом `/auth/refresh` старая запись
  refresh-токена в БД помечается `is_revoked=true` и `replaced_by_id`
  ставится на новый id; выдаётся новая пара access+refresh.
- **Replay-защита:** если клиент пытается использовать уже-revoked
  refresh, **все** его refresh-токены инвалидируются — сигнал
  компрометации.
- **Logout:** record refresh-токена помечается revoked, jti
  access-токена кладётся в Redis-denylist на остаток его TTL. На
  каждом запросе access-cookie проверяется против denylist.
- В БД хранится только SHA-256 хеш refresh-токена, не сам токен:
  компрометация дампа БД не выдаёт активные refresh-токены.

### Argon2 для хеша паролей

Argon2 через `argon2-cffi` — победитель PHC competition, defacto-
стандарт для парольных хешей в 2024+. Параметры по умолчанию
библиотеки (на 2026 год — 64MB / 3 итерации / 4 параллельности)
адекватны для production. Проверка `needs_rehash` на каждом login
позволяет прозрачно переходить на более тяжёлые параметры.

### Password policy

Минимум 12 символов, обязательны буква (любая, латиница или кириллица)
и цифра. Реализовано в `auth.domain.value_objects.assert_password_policy`,
проверяется при `CreateUser` и при смене пароля. Без проверки против
списка leaked-паролей — это отдельная задача после появления
notifier-сервиса.

### RBAC: Casbin с моделью «RBAC with domains», policy в БД

Модель Casbin `model.conf`:

```
[request_definition]
r = sub, dom, obj, act

[policy_definition]
p = sub, dom, obj, act

[role_definition]
g = _, _, _

[matchers]
m = g(r.sub, p.sub, r.dom)
    && (p.dom == "*" || p.dom == r.dom)
    && r.obj == p.obj && r.act == p.act
```

- `sub` — `user_id`.
- `dom` — `organization_id`. Это бизнес-разделение внутри инстанса
  (см. ADR-0009), не security-tenant.
- `obj` / `act` — формат permission'а: `<resource>:<action>`.

Permissions роли привязаны к `dom = "*"` (любая организация холдинга);
конкретная organization приходит через grouping policy
`g(user_id, role_name, organization_id)` — её добавляет UseCase при
создании membership.

**Policy storage:** Postgres (та же БД, что и прикладные данные)
через `casbin-async-sqlalchemy-adapter`. Это согласуется с
single-tenant-моделью — отдельный инстанс БД под policy не оправдан.

**Роли — настраиваемые:** хранятся в таблице `roles`; bootstrap
создаёт три системные роли (`owner`, `admin`, `member`) с базовым
permission-набором. Это часть курса на Frappe-style RBAC (см. memory).

### Permission storage: таблица `permissions` с полем `level`

Таблица `permissions(id, resource, action, level, description)`. На
этом этапе `level` всегда 0 — поле зарезервировано под Frappe-style
permission levels (доступ к конкретным полям ресурса по уровню).

`role_permissions(role_id, permission_id)` — связь роли с её
permissions. Casbin policy таблица `casbin_rule` синхронизируется с
`role_permissions` при bootstrap'е (на текущем этапе — однократно
через `SetupInstance`).

## Последствия

### Положительные

- Стандартный, проверенный в продакшене стек: JWT cookies, Argon2,
  Casbin.
- Переключение между организациями — без re-login; URL отражает
  контекст.
- Real logout (через denylist) — украденный токен можно отозвать в
  пределах 15 минут максимум.
- Архитектура готова к расширению до Frappe-style RBAC без слома
  схемы.

### Отрицательные / компромиссы

- `denylist:contains` — лишний Redis-вызов на каждом авторизованном
  запросе. На single-tenant-deploy это не проблема, но в условном
  будущем SaaS-варианте потребовалось бы локальное кеширование.
- Casbin policy в БД — лишняя таблица `casbin_rule`, которую тоже
  нужно бэкапить.
- В dev `cookie_secure=false` — на лисёрчинге и по чужим Wi-Fi токены
  передаются открыто. Прод обязан переключить на `true`.

## Альтернативы

### Token storage: localStorage / Authorization header

Безопасно при условии надёжной защиты от XSS. Но XSS-атака в
обходящем CSP-сценарии даёт прямой доступ к токенам — это известный
вектор. httpOnly cookies этот класс атак закрывает.

### RBAC без domain (один permission на ресурс/действие)

Проще, но не позволяет одной роли работать в одной организации и
отсутствовать в другой — а это базовый сценарий C-варианта (см.
ADR-0009).

### OAuth2 password flow с access-token-only

Без refresh: пользователь либо мирится с коротким access TTL и частым
re-login, либо TTL делается длинным — и тогда теряется реальная
логаут-семантика. Refresh + rotation — стандартная середина.

### bcrypt вместо Argon2

bcrypt всё ещё корректен, но Argon2 предпочтительнее при равной
сложности интеграции. Argon2 победил в PHC competition; bcrypt
устаревает (но безопасен).
