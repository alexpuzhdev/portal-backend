.PHONY: install run stop migrate migration lint format types imports test test-unit test-integration check pre-commit-install

# Список Python-сервисов внутри apps/. Когда появляются новые сервисы (connector-mock, notifier),
# добавляются сюда — и весь набор make-целей автоматически их учитывает.
SERVICES := core

install:
	uv sync --all-packages

pre-commit-install:
	uv run pre-commit install

run:
	docker compose -f infra/docker-compose.dev.yml up

stop:
	docker compose -f infra/docker-compose.dev.yml down

migrate:
	cd apps/core && uv run alembic upgrade head

migration:
	@test -n "$(m)" || (echo "Usage: make migration m=\"description\"" && exit 1)
	cd apps/core && uv run alembic revision --autogenerate -m "$(m)"

lint:
	uv run ruff check .

format:
	uv run ruff format .

types:
	@for svc in $(SERVICES); do \
		echo "==> mypy apps/$$svc"; \
		(cd apps/$$svc && uv run mypy app) || exit 1; \
	done
	@for pkg in packages/*/; do \
		echo "==> mypy $$pkg"; \
		(cd $$pkg && uv run mypy .) || exit 1; \
	done

imports:
	@for svc in $(SERVICES); do \
		echo "==> lint-imports apps/$$svc"; \
		(cd apps/$$svc && uv run lint-imports) || exit 1; \
	done

test:
	uv run pytest \
	    apps/*/tests \
	    apps/*/app/modules/*/tests \
	    packages/*/tests

test-unit:
	uv run pytest \
	    apps/*/tests/unit \
	    apps/*/app/modules/*/tests/unit \
	    packages/*/tests

test-integration:
	uv run pytest \
	    apps/*/tests/integration \
	    apps/*/app/modules/*/tests/integration

# Внутри блоков этапа gate сводится к статическим проверкам — тесты
# пишутся отдельным финальным блоком (см. memory feedback_test_cadence).
# Когда появится полный test-suite, добавим `test-unit` обратно в check.
check: lint types imports
