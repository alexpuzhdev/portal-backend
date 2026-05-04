"""Общие фикстуры для тестов apps/core.

Integration-тесты ожидают, что доступен Postgres из docker-compose.dev.
Тесты создают изолированную тестовую БД на каждый прогон, чтобы не
портить dev-окружение.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio

# Импорты ORM-моделей по модулям — собирают metadata в Base. Без них
# create_all не увидит таблицы. Тот же приём, что в alembic/env.py.
from app.modules.auth.infrastructure.persistence import (
    orm as _auth_orm,  # noqa: F401
)
from app.modules.organizations.infrastructure.persistence import (
    orm as _organizations_orm,  # noqa: F401
)
from app.shared.infrastructure.db.base import Base
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

target_metadata = Base.metadata


def _test_database_url() -> str:
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://portal:portal@localhost:5432/portal_test",
    )


@pytest.fixture(scope="session")
def db_engine() -> Iterator[AsyncEngine]:
    """Engine на всю сессию тестов. NullPool обязателен: pytest-asyncio
    создаёт новый event loop для каждого теста, а пул соединений
    asyncpg прибивается к loop, в котором соединение было открыто.
    NullPool открывает свежее соединение под каждый запрос — нет
    переиспользования между event loops."""
    engine = create_async_engine(_test_database_url(), echo=False, poolclass=NullPool)
    yield engine


_schema_initialised = False


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Чистая сессия на каждый тест.

    На первом обращении пересоздаёт схему (drop_all + create_all),
    чтобы не зависеть от состояния, оставленного предыдущими прогонами.
    Дальше каждый тест работает в своей транзакции, которая
    откатывается на teardown — так тесты не видят друг друга.
    """
    global _schema_initialised
    if not _schema_initialised:
        async with db_engine.begin() as conn:
            await conn.run_sync(target_metadata.drop_all)
            await conn.run_sync(target_metadata.create_all)
        _schema_initialised = True

    connection = await db_engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    return asyncio.DefaultEventLoopPolicy()
