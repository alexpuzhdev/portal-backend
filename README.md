# portal-backend

[![CI](https://github.com/alexpuzhdev/portal-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/alexpuzhdev/portal-backend/actions/workflows/ci.yml)

Backend Portal — модульная платформа корпоративного и клиентского
портала для малого бизнеса. Этот репозиторий содержит:

- **`apps/core`** — ядро платформы (FastAPI, модульный монолит).
- **`apps/connector-mock`** *(появится позже)* — референсный коннектор.
- **`apps/notifier`** *(появится позже)* — сервис уведомлений.
- **`packages/canonical-models`** — Pydantic-модели канона.
- **`packages/connector-sdk`** — базовые классы для коннекторов.
- **`packages/event-schemas`** — Pydantic-схемы событий шины.

Фронтенд живёт отдельно: [portal-frontend](https://github.com/alexpuzhdev/portal-frontend).

## Документация

- [Архитектура](docs/architecture.md)
- [Локальная разработка](docs/local-development.md)
- [Архитектурные решения (ADR)](docs/adr/)
- [Правила разработки и шаблоны кода](CLAUDE.md)

## Быстрый старт

```bash
make install              # uv sync --all-packages
make pre-commit-install   # один раз на клон
cp .env.example .env
make run                  # postgres, redis, rabbitmq, minio, core
curl http://localhost:8000/health
```

Подробности — в [docs/local-development.md](docs/local-development.md).

## Лицензия

[MIT](LICENSE)
