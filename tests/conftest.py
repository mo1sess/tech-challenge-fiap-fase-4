from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(tmp_path) -> AsyncGenerator[AsyncClient, None]:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        storage_dir=tmp_path / "uploads",
        cors_origins=["http://testserver"],
    )
    app = create_app(settings)
    Base.metadata.create_all(bind=app.state.engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.state.engine.dispose()


@pytest.fixture
async def patient(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/patients",
        json={
            "code": "MG-TEST-001",
            "alias": "Paciente Sintetico Teste",
            "birth_year": 1990,
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201
    return response.json()

