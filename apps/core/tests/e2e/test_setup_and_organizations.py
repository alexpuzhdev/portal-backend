from collections.abc import AsyncIterator

import pytest
from app.core.app_factory import create_app
from app.shared.infrastructure.db import get_session
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def app(db_session: AsyncSession):
    application = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        # Возвращаем уже-открытую сессию из тестовой фикстуры. Никакого
        # commit здесь — он бы выходил за границу теста; внешняя
        # транзакция conftest откатит всё после теста.
        yield db_session

    application.dependency_overrides[get_session] = override_get_session
    return application


@pytest.mark.asyncio
async def test_setup_creates_root_then_409_on_repeat(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/setup",
            json={"organization": {"slug": "alpha", "name": "Alpha Holding"}},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["organization"]["slug"] == "alpha"
        assert body["organization"]["parent_organization_id"] is None

        # Повторный вызов — instance уже инициализирован.
        response = await client.post(
            "/setup",
            json={"organization": {"slug": "beta", "name": "Beta"}},
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_organization_after_setup(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post(
            "/setup",
            json={"organization": {"slug": "alpha", "name": "Alpha"}},
        )

        response = await client.get("/organizations/alpha")
        assert response.status_code == 200
        assert response.json()["slug"] == "alpha"

        response = await client.get("/organizations/missing")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_setup_rejects_invalid_slug(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/setup",
            json={"organization": {"slug": "Invalid Slug!", "name": "X"}},
        )
        assert response.status_code == 422
