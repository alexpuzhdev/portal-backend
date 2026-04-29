# Локальная разработка

## Предварительные требования

| Инструмент | Версия |
|------------|--------|
| Python | 3.12+ (uv поставит сам) |
| [uv](https://docs.astral.sh/uv/) | 0.11+ |
| Docker | 24+ |
| Docker Compose | v2 (плагин `docker compose`, не legacy `docker-compose`) |
| GNU Make | 4+ |

uv можно поставить одной командой:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Первый запуск

```bash
git clone https://github.com/alexpuzhdev/portal-backend.git
cd portal-backend

# Установка зависимостей всего workspace (apps/* + packages/*).
make install

# Установка pre-commit хуков (один раз на клон).
make pre-commit-install

# Локальный конфиг.
cp .env.example .env
# при необходимости — поправь значения под себя

# Поднять postgres, redis, rabbitmq, minio и core.
make run
```

`make run` собирает образ core, скачивает зависимости postgres/redis/
rabbitmq/minio и поднимает всё c hot-reload. Первый запуск — несколько
минут, последующие — быстро.

После `make run` доступны:

| Сервис | URL |
|--------|-----|
| Core API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| RabbitMQ management | http://localhost:15672 (portal / portal) |
| MinIO console | http://localhost:9001 (portal / portalpassword) |
| Redis (для отладки) | localhost:**16379** (нестандартный порт, см. ниже) |
| Postgres (для отладки) | localhost:5432 (portal / portal / portal) |

> Redis проброшен на нестандартный хост-порт `16379`, чтобы не
> конфликтовать с системным Redis, который часто стоит на машинах
> разработки. Внутри compose сервис всегда доступен как `redis:6379` —
> приложение это не замечает.

Проверка:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Останавливать стек:

```bash
make stop
```

## Команды

```bash
make install         # uv sync --all-packages
make pre-commit-install  # установить pre-commit хуки
make run             # docker compose up
make stop            # docker compose down
make migrate         # alembic upgrade head
make migration m="add users table"
                     # alembic revision --autogenerate
make lint            # ruff check
make format          # ruff format
make types           # mypy по всем сервисам и пакетам
make imports         # import-linter по всем сервисам
make test            # все тесты
make test-unit       # только unit-тесты
make test-integration  # только integration-тесты (требуют поднятой БД)
make check           # lint + types + imports + test-unit (запускается перед PR)
```

## Как добавить новый модуль ядра

См. шаблон в `CLAUDE.md`, раздел «Структура модуля». Кратко:

1. Создать `apps/core/app/modules/<name>/` с четырьмя слоями: `domain`,
   `application`, `infrastructure`, `presentation`.
2. Добавить контракт зависимостей в `apps/core/.importlinter`:
   ```ini
   [importlinter:contract:<name>-clean-architecture]
   name = Clean Architecture - <name> module
   type = layers
   layers =
       app.modules.<name>.presentation
       app.modules.<name>.infrastructure
       app.modules.<name>.application
       app.modules.<name>.domain
   ```
3. Зарегистрировать роутер модуля в `app/main.py` (когда появится
   соответствующая инфраструктура).
4. Добавить тесты в `apps/core/tests/unit/<name>/` и
   `apps/core/tests/integration/<name>/`.

## Как добавить новый сервис (коннектор/notifier)

1. Создать `apps/<name>/` с собственным `pyproject.toml` и
   `Dockerfile`.
2. Добавить путь сервиса в переменную `SERVICES` в `Makefile` —
   `make types` и `make imports` подхватят его автоматически.
3. Описать сервис в `docker-compose.dev.yml`.
4. Добавить контракт зависимостей: `apps/<name>/.importlinter`.
5. Контракт с ядром — события в `packages/event-schemas`.

## Миграции БД

```bash
# Создать миграцию (автогенерация по diff моделей)
make migration m="create products table"

# Прочитать сгенерированный файл вручную перед коммитом — autogenerate
# периодически создаёт лишние или некорректные изменения.

# Применить миграции локально
make migrate
```

Правила миграций — в `CLAUDE.md`, раздел «Миграции БД».

## Если что-то пошло не так

| Симптом | Что делать |
|---------|------------|
| `make install` падает на установке asyncpg | Установить системные `libpq-dev` и `postgresql-server-dev-all`, либо положиться на колесо asyncpg |
| `docker compose` не видит сервисов | Проверить, что используется плагин `docker compose`, а не legacy `docker-compose` |
| RabbitMQ не успевает стать healthy | На старте контейнера это нормально (~30 секунд), `core` стартует после healthcheck |
| Тесты не находятся (`no tests collected`) | Проверить, что выполняется из корня репозитория и `pyproject.toml` содержит `pytest.ini_options.testpaths` или путь явно передан |
| `address already in use` на каком-то порту | Системный сервис на хосте занял порт. Поправить хост-маппинг в `infra/docker-compose.dev.yml` (например, `15432:5432` вместо `5432:5432`). Внутрисервисное общение идёт по именам сервисов и не зависит от хост-портов. |

## Что дальше

- Структура модуля и шаблоны кода — `CLAUDE.md`
- Архитектурные решения — `docs/architecture.md` и `docs/adr/`
- Канонические модели — `docs/canonical-models.md` (появится по мере
  заполнения канона)
- Гайд по написанию коннектора — `docs/connector-guide.md` (появится
  с первым реальным коннектором)
