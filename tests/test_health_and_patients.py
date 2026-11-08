import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_rejects_non_synthetic_patient(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/patients",
        json={"code": "REAL-001", "alias": "Nao permitido", "is_synthetic": False},
    )
    assert response.status_code == 422

