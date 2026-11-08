import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_normal_measurement_creates_no_alert(client: AsyncClient, patient: dict) -> None:
    response = await client.post(
        f"/api/v1/patients/{patient['id']}/measurements",
        json={
            "heart_rate_bpm": 80,
            "spo2_percent": 98,
            "systolic_mmhg": 120,
            "diastolic_mmhg": 80,
            "is_synthetic": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["events"] == []
    assert response.json()["alerts"] == []


async def test_demo_creates_critical_event_and_alert(client: AsyncClient) -> None:
    response = await client.post("/api/v1/demo/vital-alert")
    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["is_synthetic"] is True
    assert body["result"]["events"][0]["severity"] == "critical"
    assert body["result"]["alerts"][0]["status"] == "open"

    alerts = await client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    assert len(alerts.json()) == 1

