# Архитектура backend Portal

Этот документ — карта верхнего уровня. Подробности по конкретным
решениям — в `docs/adr/`. Конкретные шаблоны кода и структура модулей —
в `CLAUDE.md` репозитория.

## Состав платформы

```
                    ┌───────────────────────────┐
                    │   Frontend (Next.js)      │
                    │   portal-frontend         │
                    └─────────────┬─────────────┘
                                  │ REST + WebSocket
                                  ▼
                    ┌───────────────────────────┐
                    │   Core API (FastAPI)      │
                    │   apps/core               │
                    │   модули: auth, orgs,     │
                    │   feed, catalog,          │
                    │   requests, ...           │
                    └─────────────┬─────────────┘
                                  │ RabbitMQ (events)
              ┌───────────────────┼─────────────────────┐
              │                   │                     │
        ┌─────▼─────┐       ┌─────▼─────┐         ┌─────▼─────┐
        │ Connector │       │ Notifier  │         │ ...       │
        │   Mock    │       │  Service  │         │           │
        │ apps/     │       │ apps/     │         │           │
        │ connector-│       │ notifier  │         │           │
        │ mock      │       │           │         │           │
        └───────────┘       └───────────┘         └───────────┘
```

Дополнительно:

- **PostgreSQL 16** — основная БД ядра. Один деплой Portal обслуживает
  одну организацию-клиента (single-tenant per deployment, см.
  [ADR-0009](adr/0009-single-tenant-per-deployment.md)) — изоляция между
  клиентами обеспечивается отдельными деплоями, в БД нет колонок
  `organization_id`/`tenant_id`.
- **Redis 7** — кэш, сессии, broker для arq (фоновые задачи).
- **RabbitMQ** — шина событий между сервисами.
- **MinIO / Selectel S3** — объектное хранилище.

## Ключевые архитектурные решения

| ADR | Решение |
|-----|---------|
| [0001](adr/0001-modular-monolith-for-core.md) | Ядро — модульный монолит, не микросервисы |
| [0002](adr/0002-connectors-as-separate-services.md) | Коннекторы и notifier — отдельные сервисы |
| [0003](adr/0003-canonical-models-as-integration-contract.md) | Канонические модели — единственный источник истины |
| [0004](adr/0004-multi-tenancy-via-organization-id.md) | ~~Multi-tenancy через `organization_id`~~ — **устарело**, заменено на 0009 |
| [0005](adr/0005-rabbitmq-as-event-bus.md) | RabbitMQ как шина событий |
| [0006](adr/0006-two-repo-split.md) | Разделение проекта на backend и frontend репозитории |
| [0007](adr/0007-clean-architecture.md) | Clean Architecture внутри Python-сервисов |
| [0008](adr/0008-oop-first-with-functional-routes.md) | ООП-first для бизнес-кода, функции для FastAPI роутов |
| [0009](adr/0009-single-tenant-per-deployment.md) | Single-tenant per deployment (один инстанс — одна организация) |

## Правила, не подлежащие переоткрытию без ADR

1. **Модульный монолит для ядра.** Любое предложение «вынесем модуль X в
   отдельный сервис» — через новый ADR.
2. **Канон — единственный источник истины.** Внутрь ядра не попадают
   данные «в формате внешней системы».
3. **Single-tenant per deployment.** Один инстанс обслуживает одну
   организацию-клиента. В БД нет `organization_id`/`tenant_id`. Сущность
   `Organization` остаётся, но в таблице ровно одна строка — профиль
   компании-владельца инстанса.
4. **Event-driven между сервисами, sync внутри сервиса.** Между ядром и
   коннекторами — только события. Внутри сервиса — обычные вызовы.
5. **Sync API — только для чтения.** Изменения во внешних системах ядро
   делает через события, не через прямой вызов API коннектора.
6. **Никакой бизнес-логики в роутах.** Роут — парсинг + вызов UseCase +
   ответ.
7. **Каждый модуль владеет своими данными.** Прямые JOIN'ы между
   таблицами разных модулей запрещены; доступ — через сервисный слой
   или события.

## Структура репозитория

```
portal-backend/
├── apps/                     # сервисы (один процесс — один app)
│   └── core/                 # ядро портала (модульный монолит)
├── packages/                 # path-зависимости workspace
│   ├── canonical-models/     # Pydantic-модели канона
│   ├── connector-sdk/        # базовые классы для коннекторов
│   └── event-schemas/        # Pydantic-схемы событий
├── infra/                    # docker-compose
├── docs/                     # эта документация и ADR
├── scripts/                  # утилиты, миграционные скрипты
├── .github/workflows/        # CI
├── CLAUDE.md                 # правила для агента и разработчика
├── Makefile                  # единые команды
└── pyproject.toml            # uv workspace
```

## Слои Clean Architecture (внутри каждого сервиса)

См. [ADR-0007](adr/0007-clean-architecture.md) и `CLAUDE.md`.

```
HTTP request
     ↓
presentation/routes.py     ← FastAPI функция
     ↓ парсит → presentation/schemas.py (Pydantic)
     ↓ вызывает через Depends
application/use_cases/*.py ← UseCase (класс с execute)
     ↓ работает с
domain/entities.py         ← Entity (класс с поведением)
domain/repositories.py     ← Protocol
     ↓ Protocol реализован в
infrastructure/persistence/repositories.py
     ↓ маппит через
infrastructure/persistence/mappers.py
     ↓
PostgreSQL
```

Правило зависимостей: стрелки только наружу.
`domain` не знает про `application`, `infrastructure`, `presentation`.
`application` не знает про `infrastructure` и `presentation`.
Это проверяется автоматически через `import-linter`.

## Где что живёт

| Что | Где |
|-----|-----|
| Бизнес-сущность (Product, Order) | `apps/core/app/modules/<name>/domain/entities.py` |
| Сценарий (CreateProduct) | `apps/core/app/modules/<name>/application/use_cases/` |
| SQLAlchemy модель | `apps/core/app/modules/<name>/infrastructure/persistence/orm.py` |
| FastAPI роут | `apps/core/app/modules/<name>/presentation/routes.py` |
| Канонические модели | `packages/canonical-models/canonical_models/` |
| Схемы событий | `packages/event-schemas/event_schemas/` |
| Базовые классы коннектора | `packages/connector-sdk/connector_sdk/` |

## Контракты с внешним миром

- **С фронтом** — REST + WebSocket. OpenAPI генерируется ядром, фронт
  на основе OpenAPI генерирует TypeScript-типы.
- **С коннекторами** — события в RabbitMQ в каноническом формате.
  Имена событий: `<module>.<entity>.<action>`. Версионирование — через
  поле `version` в payload.
- **С внешними системами** — только через коннекторы. Ядро не имеет
  HTTP-клиентов к внешним CRM/ERP напрямую.

## Что отложено за рамки MVP

- Multi-region deploy.
- Read-replicas Postgres и шардирование.
- Outbox pattern для транзакционной публикации событий (если
  потребуется — отдельный ADR).
- PostgreSQL Row-Level Security как defense in depth.
- Сторонние коннекторы в отдельных репозиториях.
