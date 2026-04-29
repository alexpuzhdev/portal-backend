# backend/CLAUDE.md — Portal Backend

Этот файл — специфика для Python-сервисов проекта (ядро, коннекторы,
notifier). Дополняет корневой `CLAUDE.md` (находится в
`portal-project/CLAUDE.md`). Корневой читается обязательно — здесь только
backend-конкретика.

## Структура репозитория

```
portal-backend/
├── apps/
│   ├── core/                       # ядро портала
│   │   ├── app/
│   │   │   ├── modules/            # модули ядра (см. ниже)
│   │   │   ├── shared/             # общий код модулей
│   │   │   ├── core/               # config, security, app builder
│   │   │   └── main.py
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── connector-mock/             # референсный коннектор
│   └── notifier/                   # сервис нотификаций
├── packages/
│   ├── canonical-models/           # Pydantic схемы канона
│   ├── connector-sdk/              # базовые классы для коннекторов
│   └── event-schemas/              # Pydantic схемы событий
├── infra/
│   ├── docker-compose.yml          # прод-подобный
│   └── docker-compose.dev.yml      # dev с hot-reload
├── docs/
│   ├── adr/                        # architecture decision records
│   ├── architecture.md
│   ├── canonical-models.md
│   ├── connector-guide.md
│   └── local-development.md
├── scripts/                        # утилиты, миграционные скрипты
├── .github/workflows/
├── CLAUDE.md                       # этот файл
├── Makefile                        # единые команды для всех apps
├── pyproject.toml                  # workspace конфигурация (uv)
└── README.md
```

`packages/` подключаются в `apps/*/pyproject.toml` как path-зависимости.
Все управление через **uv workspace** — один `uv sync` из корня
устанавливает зависимости всех apps и packages.

## Структура модуля (Clean Architecture)

Каждый модуль ядра (`apps/core/app/modules/<name>/`) и каждый коннектор
имеют **одинаковую** структуру слоёв:

```
modules/<name>/
├── domain/
│   ├── __init__.py
│   ├── entities.py          # бизнес-сущности (классы)
│   ├── value_objects.py     # неизменяемые значения (frozen dataclass)
│   ├── exceptions.py        # доменные исключения
│   └── repositories.py      # Protocol для repository
├── application/
│   ├── __init__.py
│   ├── use_cases/
│   │   ├── __init__.py
│   │   ├── create_<entity>.py
│   │   ├── update_<entity>.py
│   │   ├── list_<entities>.py
│   │   └── ...
│   ├── dto.py               # внутренние DTO между слоями
│   └── ports.py             # Protocol для внешних систем (event bus, etc)
├── infrastructure/
│   ├── __init__.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── orm.py           # SQLAlchemy модели
│   │   ├── mappers.py       # Entity ↔ ORM конвертация
│   │   └── repositories.py  # реализация repository protocol
│   ├── events/
│   │   ├── __init__.py
│   │   └── publisher.py     # реализация event publisher
│   └── ...
├── presentation/
│   ├── __init__.py
│   ├── schemas.py           # Pydantic request/response
│   ├── routes.py            # FastAPI роуты (функции)
│   └── deps.py              # Depends-функции для DI
├── tests/
│   ├── unit/                # тесты domain и application
│   ├── integration/         # тесты infrastructure (с тестовой БД)
│   └── e2e/                 # тесты роутов через httpx.AsyncClient
└── __init__.py              # экспортирует публичный API модуля
```

**Правило зависимостей:**

```
presentation → application → domain
infrastructure → application → domain
```

Никогда наоборот. Это проверяется автоматически (см. ниже про
`import-linter`).

**Что куда:**

| Что | Куда | Стиль |
|-----|------|-------|
| Бизнес-сущность с правилами (Product, Order) | `domain/entities.py` | класс |
| Неизменяемое значение (Money, SKU, Email) | `domain/value_objects.py` | `@dataclass(frozen=True)` |
| Бизнес-исключение (ProductNotFound) | `domain/exceptions.py` | класс-наследник Exception |
| Интерфейс repository | `domain/repositories.py` | `Protocol` |
| Сценарий "создать продукт" | `application/use_cases/create_product.py` | класс UseCase |
| DTO для ввода UseCase | `application/dto.py` | `@dataclass(frozen=True)` или Pydantic |
| Реализация repository | `infrastructure/persistence/repositories.py` | класс |
| SQLAlchemy модель | `infrastructure/persistence/orm.py` | класс ORM |
| Mapper Entity ↔ ORM | `infrastructure/persistence/mappers.py` | класс или функции |
| Реализация event publisher | `infrastructure/events/publisher.py` | класс |
| Pydantic-схема API | `presentation/schemas.py` | класс BaseModel |
| FastAPI роут | `presentation/routes.py` | функция |
| Depends для UseCase | `presentation/deps.py` | функция |

## Шаблоны кода

### Entity (domain)

```python
# domain/entities.py
from dataclasses import dataclass
from uuid import UUID

from .value_objects import Money, SKU
from .exceptions import InvalidProductState


@dataclass
class Product:
    id: UUID
    organization_id: UUID
    sku: SKU
    name: str
    price: Money
    is_active: bool

    def deactivate(self) -> None:
        if not self.is_active:
            raise InvalidProductState("Product is already inactive")
        self.is_active = False

    def change_price(self, new_price: Money) -> None:
        if new_price.amount <= 0:
            raise InvalidProductState("Price must be positive")
        self.price = new_price
```

Entity содержит **поведение**, не только данные. Бизнес-правила — здесь.

### Value Object (domain)

```python
# domain/value_objects.py
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "RUB"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
```

Value object — `frozen=True`. Сравнение по значению, не по идентичности.

### Repository Protocol (domain)

```python
# domain/repositories.py
from typing import Protocol
from uuid import UUID

from .entities import Product


class ProductRepository(Protocol):
    async def get_by_id(
        self, product_id: UUID, organization_id: UUID
    ) -> Product | None: ...

    async def list_by_organization(
        self, organization_id: UUID, limit: int, offset: int
    ) -> list[Product]: ...

    async def add(self, product: Product) -> None: ...

    async def update(self, product: Product) -> None: ...
```

`Protocol`, не ABC. Это даёт structural typing и не требует наследования
от реализаций. Каждый метод принимает `organization_id` явно — это часть
контракта tenant isolation.

### UseCase (application)

```python
# application/use_cases/create_product.py
from dataclasses import dataclass
from uuid import UUID, uuid4

from ...domain.entities import Product
from ...domain.repositories import ProductRepository
from ...domain.value_objects import Money, SKU
from ..ports import EventPublisher
from ..dto import CreateProductInput, ProductOutput


@dataclass
class CreateProduct:
    repository: ProductRepository
    events: EventPublisher

    async def execute(
        self, input_dto: CreateProductInput, organization_id: UUID
    ) -> ProductOutput:
        product = Product(
            id=uuid4(),
            organization_id=organization_id,
            sku=SKU(input_dto.sku),
            name=input_dto.name,
            price=Money(input_dto.price_amount, input_dto.price_currency),
            is_active=True,
        )
        await self.repository.add(product)
        await self.events.publish(
            "catalog.product.created",
            {"product_id": str(product.id), "organization_id": str(organization_id)},
        )
        return ProductOutput.from_entity(product)
```

UseCase — **класс с одним методом `execute`**. Зависимости — через
конструктор (dataclass с полями). Один UseCase = один сценарий.

### DTO (application)

```python
# application/dto.py
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ..domain.entities import Product


@dataclass(frozen=True)
class CreateProductInput:
    sku: str
    name: str
    price_amount: Decimal
    price_currency: str = "RUB"


@dataclass(frozen=True)
class ProductOutput:
    id: UUID
    sku: str
    name: str
    price_amount: Decimal
    price_currency: str
    is_active: bool

    @classmethod
    def from_entity(cls, product: Product) -> "ProductOutput":
        return cls(
            id=product.id,
            sku=str(product.sku),
            name=product.name,
            price_amount=product.price.amount,
            price_currency=product.price.currency,
            is_active=product.is_active,
        )
```

DTO — **внутренние** структуры между слоями. Не путать с Pydantic-схемами
API (те живут в `presentation/schemas.py`).

### ORM model (infrastructure)

```python
# infrastructure/persistence/orm.py
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import Base


class ProductORM(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

ORM-модель **отделена** от Entity. Не смешивать. ORM — это хранилище,
Entity — это бизнес-сущность.

### Mapper (infrastructure)

```python
# infrastructure/persistence/mappers.py
from ...domain.entities import Product
from ...domain.value_objects import Money, SKU
from .orm import ProductORM


class ProductMapper:
    @staticmethod
    def to_entity(orm: ProductORM) -> Product:
        return Product(
            id=orm.id,
            organization_id=orm.organization_id,
            sku=SKU(orm.sku),
            name=orm.name,
            price=Money(orm.price_amount, orm.price_currency),
            is_active=orm.is_active,
        )

    @staticmethod
    def to_orm(entity: Product) -> ProductORM:
        return ProductORM(
            id=entity.id,
            organization_id=entity.organization_id,
            sku=str(entity.sku),
            name=entity.name,
            price_amount=entity.price.amount,
            price_currency=entity.price.currency,
            is_active=entity.is_active,
        )
```

### Repository implementation (infrastructure)

```python
# infrastructure/persistence/repositories.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import Product
from .mappers import ProductMapper
from .orm import ProductORM


class SqlProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, product_id: UUID, organization_id: UUID
    ) -> Product | None:
        stmt = select(ProductORM).where(
            ProductORM.id == product_id,
            ProductORM.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return ProductMapper.to_entity(orm) if orm else None

    async def list_by_organization(
        self, organization_id: UUID, limit: int, offset: int
    ) -> list[Product]:
        stmt = (
            select(ProductORM)
            .where(ProductORM.organization_id == organization_id)
            .limit(limit)
            .offset(offset)
            .order_by(ProductORM.name)
        )
        result = await self._session.execute(stmt)
        return [ProductMapper.to_entity(orm) for orm in result.scalars()]

    async def add(self, product: Product) -> None:
        orm = ProductMapper.to_orm(product)
        self._session.add(orm)
        await self._session.flush()

    async def update(self, product: Product) -> None:
        orm = await self._session.get(ProductORM, product.id)
        if orm is None or orm.organization_id != product.organization_id:
            raise ValueError("Product not found in organization")
        # обновляем поля
        orm.name = product.name
        orm.price_amount = product.price.amount
        orm.price_currency = product.price.currency
        orm.is_active = product.is_active
        await self._session.flush()
```

**Каждый запрос фильтруется по `organization_id`.** Это критично.

### Pydantic schema (presentation)

```python
# presentation/schemas.py
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateProductRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    price_amount: Decimal = Field(..., gt=0)
    price_currency: str = Field("RUB", min_length=3, max_length=3)


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    price_amount: Decimal
    price_currency: str
    is_active: bool
```

Pydantic-схемы только для **внешнего API**. Между слоями — `dataclass`-DTO.

### Depends (presentation)

```python
# presentation/deps.py
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.db import get_session
from app.shared.infrastructure.events import get_event_publisher

from ..application.use_cases.create_product import CreateProduct
from ..infrastructure.persistence.repositories import SqlProductRepository


def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlProductRepository:
    return SqlProductRepository(session)


def get_create_product(
    repository: Annotated[SqlProductRepository, Depends(get_product_repository)],
    events=Depends(get_event_publisher),
) -> CreateProduct:
    return CreateProduct(repository=repository, events=events)
```

DI выстраивается слоями: session → repository → use case. Каждый Depends
— тонкая функция.

### Route (presentation)

```python
# presentation/routes.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.shared.presentation.auth import current_organization

from ..application.dto import CreateProductInput
from ..application.use_cases.create_product import CreateProduct
from .deps import get_create_product
from .schemas import CreateProductRequest, ProductResponse

router = APIRouter(prefix="/products", tags=["catalog"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: CreateProductRequest,
    organization_id: Annotated[UUID, Depends(current_organization)],
    use_case: Annotated[CreateProduct, Depends(get_create_product)],
) -> ProductResponse:
    input_dto = CreateProductInput(
        sku=request.sku,
        name=request.name,
        price_amount=request.price_amount,
        price_currency=request.price_currency,
    )
    output = await use_case.execute(input_dto, organization_id=organization_id)
    return ProductResponse(
        id=output.id,
        sku=output.sku,
        name=output.name,
        price_amount=output.price_amount,
        price_currency=output.price_currency,
        is_active=output.is_active,
    )
```

**Что делает роут:**
1. Принимает Pydantic-запрос
2. Получает `organization_id` из контекста (auth middleware кладёт его туда)
3. Получает UseCase через Depends
4. Конвертирует Pydantic → DTO
5. Вызывает UseCase
6. Конвертирует DTO → Pydantic ответ

**Никакой бизнес-логики.** Всё в UseCase и Entity.

## FastAPI: специфика и ограничения

- Роуты — функции, не классы. Никаких `cbv` декораторов.
- DI через `Depends` — стандарт FastAPI. Не пытайся внедрять контейнер
  типа `dependency-injector` или `punq` без острой необходимости.
- Все роуты — `async def`. Синхронные хендлеры запрещены.
- Все Depends-функции, которые делают I/O, тоже async.
- `BackgroundTasks` для лёгких задач (отправить уведомление). Тяжёлое —
  через arq.

## Tenant isolation: practical patterns

Это **критичная часть безопасности**. Проверяется на каждом ревью.

### Получение organization_id

`organization_id` определяется **в auth middleware** на основе JWT-токена
пользователя. В роуте получается через `Depends(current_organization)`.

Никогда не принимай `organization_id` из тела запроса или query
параметра — это даст возможность одной организации писать данные другой.

### Repository

Каждый метод repository принимает `organization_id` явно (см. примеры выше)
и **всегда** фильтрует по нему в WHERE.

### Базовый класс OrgScopedRepository

Для типичных случаев есть базовый класс в `shared/infrastructure/db/`:

```python
# shared/infrastructure/db/repository.py
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import DeclarativeBase

OrmT = TypeVar("OrmT", bound=DeclarativeBase)


class OrgScopedRepository(Generic[OrmT]):
    """Базовый класс для repositories с обязательной фильтрацией по organization_id."""

    orm_class: type[OrmT]  # переопределяется в подклассе

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self, organization_id: UUID):
        return select(self.orm_class).where(
            self.orm_class.organization_id == organization_id  # type: ignore[attr-defined]
        )
```

Подклассы используют `_base_query` вместо `select(orm)` напрямую.

### Тесты на tenant isolation

Каждый Repository должен иметь тест:

```python
# tests/integration/test_product_repository_tenant_isolation.py
async def test_repository_does_not_leak_across_organizations(
    session, fixture_two_orgs_with_products
):
    org_a, org_b = fixture_two_orgs_with_products
    repo = SqlProductRepository(session)

    products_a = await repo.list_by_organization(org_a.id, limit=100, offset=0)
    products_b = await repo.list_by_organization(org_b.id, limit=100, offset=0)

    assert all(p.organization_id == org_a.id for p in products_a)
    assert all(p.organization_id == org_b.id for p in products_b)
    assert {p.id for p in products_a} & {p.id for p in products_b} == set()
```

## Тестирование

### Структура

- `tests/unit/` — тесты domain и application. **Без БД, без сети, без
  фреймворка.** Используют FakeRepository (in-memory реализация).
- `tests/integration/` — тесты infrastructure (repository с тестовой БД).
- `tests/e2e/` — тесты роутов через `httpx.AsyncClient` и реальную
  тестовую БД.

### FakeRepository для unit-тестов

```python
# tests/fakes/product_repository.py
from uuid import UUID

from app.modules.catalog.domain.entities import Product


class FakeProductRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Product] = {}

    async def get_by_id(
        self, product_id: UUID, organization_id: UUID
    ) -> Product | None:
        product = self._storage.get(product_id)
        if product and product.organization_id == organization_id:
            return product
        return None

    async def add(self, product: Product) -> None:
        self._storage[product.id] = product

    async def update(self, product: Product) -> None:
        self._storage[product.id] = product

    async def list_by_organization(
        self, organization_id: UUID, limit: int, offset: int
    ) -> list[Product]:
        return [
            p for p in self._storage.values()
            if p.organization_id == organization_id
        ][offset : offset + limit]
```

UseCase тестируется с FakeRepository — никаких mock-библиотек, никаких БД.

### Что тестировать обязательно

- Все доменные методы (Entity, Value Object) — unit-тесты
- Все UseCase — unit-тесты с Fake-репозиториями
- Все Repository — integration-тесты с реальной БД (включая tenant isolation)
- Критичные сценарии — e2e-тесты (auth, создание сущностей, права)

### Что тестировать опционально

- Тонкие роуты, которые только парсят и вызывают UseCase
- Mappers (Entity ↔ ORM) — обычно покрываются через integration-тесты
  repository

## Команды (Makefile)

```bash
make install        # uv sync
make run            # docker-compose up dev
make stop           # docker-compose down
make migrate        # alembic upgrade head
make migration m="message"  # alembic revision --autogenerate
make lint           # ruff check
make format         # ruff format
make types          # mypy
make imports        # import-linter
make test           # pytest
make test-unit      # pytest tests/unit
make test-integration  # pytest tests/integration
make check          # lint + types + imports + test (полная проверка перед PR)
```

## Конфигурация инструментов

### pyproject.toml — критичные настройки

- `[tool.ruff]` — line-length 100, target-version py312, set правил включает
  E, F, I, N, UP, B, A, C4, T20, SIM, RUF
- `[tool.mypy]` — `strict = true`, `disallow_untyped_defs = true`,
  `warn_return_any = true`
- `[tool.pytest.ini_options]` — asyncio_mode = "auto"

### import-linter — правило зависимостей

```toml
# .importlinter
[importlinter]
root_packages =
    app

[[importlinter.contracts]]
name = "Clean Architecture - Catalog module"
type = layers
layers =
    app.modules.catalog.presentation
    app.modules.catalog.infrastructure
    app.modules.catalog.application
    app.modules.catalog.domain
```

Для каждого модуля — свой контракт. `make imports` запускает все контракты.

## Миграции (особое внимание)

Из корневого CLAUDE.md, повторяю критичное:

- Любая миграция — `alembic revision --autogenerate -m "..."`
- **Сгенерированный файл всегда читается вручную** перед коммитом
- Миграция работает в обе стороны
- Изменения схемы и данных — отдельными ревизиями
- Никаких DROP без обсуждения

Дополнительно для проекта:

- Все таблицы бизнес-данных имеют колонку `organization_id` с FK
- Индексы по `organization_id` обязательны для всех таблиц с большим
  объёмом данных
- Composite-индексы по `(organization_id, <часто фильтруемое поле>)`

## Структура коммита

```
<type>(<scope>): <subject>

<body>

<footer>
```

- `type`: feat, fix, refactor, docs, test, chore, style, perf
- `scope`: catalog, auth, orgs, feed, requests, connector, notifier, infra
- `subject`: повелительное наклонение, lowercase, без точки, ≤72 символа
- `body`: что и зачем (опционально)
- `footer`: BREAKING CHANGE, ссылки на issues

Примеры:

- `feat(catalog): add product variants entity`
- `fix(auth): correct token expiration handling`
- `refactor(orgs): extract invitation logic to use case`
- `chore(infra): bump postgres to 16.4`

## Что проверять при ревью backend-кода

Дополняет общий чеклист в корневом CLAUDE.md:

1. **Слои чистой архитектуры:** нет ли импортов из infrastructure в
   domain/application?
2. **Tenant isolation:** все ли запросы к БД фильтруются по `organization_id`?
3. **Entity vs ORM:** нет ли смешения? Entity не должна импортировать ORM.
4. **N+1:** все relationships загружаются через `selectinload`/`joinedload`?
5. **Тесты:** UseCase покрыт unit-тестом? Repository — integration-тестом?
6. **Миграция:** что в файле alembic? Не сломает ли данные?
7. **Зависимости:** не появилось ли новых в `pyproject.toml`?
8. **Async:** нет ли sync-кода в async-роутах или UseCase?
9. **DI:** Depends-функции не содержат логику?
10. **Ошибки:** доменные исключения — в `domain/exceptions.py`, не
    `HTTPException` в UseCase?

## Обработка ошибок

- **Доменные исключения** (ProductNotFound, InvalidProductState) кидаются
  в domain или application слое
- **Маппинг в HTTP** — на уровне presentation, через FastAPI exception
  handlers (в `app/core/exceptions.py`)
- UseCase **никогда не кидает HTTPException** — это утечка фреймворка в
  application слой

Пример:

```python
# domain/exceptions.py
class ProductNotFound(Exception):
    pass

# core/exceptions.py (presentation-level)
@app.exception_handler(ProductNotFound)
async def product_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Product not found"},
    )
```
