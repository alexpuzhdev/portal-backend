# Модуль `organizations`

Управляет деревом структурных единиц холдинга: корневая организация
(сам холдинг), её юрлица, филиалы, бренды. Соответствует
[ADR-0009](../adr/0009-single-tenant-per-deployment.md): один деплой
Portal обслуживает один холдинг, организация в дереве — это
бизнес-сущность, не SaaS-арендатор.

## Domain

### Entity `Organization`

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `id` | UUID | да | первичный ключ |
| `slug` | `Slug` (VO) | да | URL-friendly идентификатор, уникален в инстансе |
| `name` | str (≤ 255) | да | отображаемое имя |
| `parent_organization_id` | UUID? | нет | NULL у корня, FK у дочерних |
| `legal_name` | str (≤ 255) | нет | юридическое наименование |
| `inn` | `INN` (VO) | нет | 10 или 12 цифр |
| `kpp` | `KPP` (VO) | нет | 9 символов |
| `primary_color_hsl` | `HSLColor` (VO) | нет | для CSS-переменной `--primary` |
| `logo_url` | str (≤ 2048) | нет | ссылка на S3-объект |
| `storefront_enabled` | bool | да (default `false`) | признак включённого публичного кабинета |
| `is_active` | bool | да (default `true`) | soft-disable |
| `created_at`, `updated_at` | datetime | да | timestamp'ы |

Поведение entity: `enable_storefront`, `disable_storefront`,
`deactivate` (запрещено для корневой), `reactivate`, `rename`.

### Value Objects

- `Slug` — `^[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?$` (URL-safe, 1..63 символа).
- `INN` — 10 или 12 цифр.
- `KPP` — формат `NNNNXXNNN` (4 цифры, 2 буквы или цифры, 3 цифры).
- `HSLColor` — формат `H S% L%` (для CSS-переменной shadcn).

### Repository protocol `OrganizationRepository`

Методы: `get_by_id`, `get_by_slug`, `get_root`, `list_all`,
`list_children`, `add`, `update`. Реализация — `SqlOrganizationRepository`
в `infrastructure/persistence/repositories.py`.

## Application

Use cases, по одному на сценарий:

- `CreateRootOrganization` — создаёт корневую (один раз на инстанс,
  повторный вызов → `RootOrganizationAlreadyExists`).
- `GetOrganizationBySlug`, `GetOrganizationById`.
- `ListOrganizations` — все организации в порядке создания.
- `UpdateOrganization` — частичное обновление полей.

DTO: `CreateRootOrganizationInput`, `UpdateOrganizationInput`,
`OrganizationOutput`.

## Infrastructure

- ORM `OrganizationORM` в `infrastructure/persistence/orm.py`.
- Маппер `OrganizationMapper` (Entity ↔ ORM).
- Реализация `SqlOrganizationRepository`.
- Миграция Alembic: `4e2244ca5c4a_create_organizations.py`.

### Гарантии в БД

- `slug` — `UNIQUE`.
- `parent_organization_id` — `FK` на саму себя с `ON DELETE RESTRICT`,
  индекс `ix_organizations_parent_organization_id`.
- **Partial unique index** `uq_organizations_single_root` на колонку
  `parent_organization_id WHERE parent_organization_id IS NULL` — гарантия
  ровно одного корня на инстанс.

## Presentation (HTTP)

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/organizations` | GET | список всех организаций инстанса |
| `/organizations/{slug}` | GET | организация по slug; 404 если не найдена |

> На текущем этапе эндпоинты публичные. После Блока 2 (auth) они будут
> закрыты `Depends(current_user)` или ограничены RBAC.

Создание корневой организации идёт через эндпоинт `/setup` модуля
[`setup`](setup.md), не через `/organizations`.

## Интеграция

- Модуль `setup` использует `CreateRootOrganization` через
  `presentation.deps.get_create_root_organization`.
- Будущий модуль `auth` будет использовать `GetOrganizationBySlug` для
  построения контекста организации в роуте.

## Архитектурный контракт

Контролируется `import-linter` (см. `apps/core/.importlinter`):

- Слои `presentation → infrastructure → application → domain`.
- Никаких импортов снизу вверх.
