import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_rising_vital_series_creates_trend_event_and_alert(
    client: AsyncClient,
    patient: dict,
) -> None:
    responses = []
    for heart_rate in [70, 82, 94, 106]:
        response = await client.post(
            f"/api/v1/patients/{patient['id']}/measurements",
            json={"heart_rate_bpm": heart_rate, "is_synthetic": True},
        )
        assert response.status_code == 201, response.text
        responses.append(response.json())

    assert all(item["events"] == [] for item in responses[:3])
    last = responses[-1]
    assert len(last["events"]) == 1
    assert last["events"][0]["source"] == "vital_trends"
    assert last["events"][0]["event_type"] == "synthetic_vital_trend_anomaly"
    assert last["events"][0]["payload"]["detections"][0]["code"] == "rising_heart_rate"
    assert len(last["alerts"]) == 1


async def test_duplicate_prescription_start_requires_review(
    client: AsyncClient,
    patient: dict,
) -> None:
    endpoint = f"/api/v1/patients/{patient['id']}/prescriptions/evaluate"
    payload = {
        "medication_code": "MED-SYNTH-001",
        "action": "started",
        "is_synthetic": True,
    }
    first = await client.post(endpoint, json=payload)
    second = await client.post(endpoint, json=payload)

    assert first.status_code == 201
    assert first.json()["events"] == []
    assert second.status_code == 201
    body = second.json()
    assert body["events"][0]["source"] == "prescription_analysis"
    assert body["events"][0]["payload"]["anomaly"] == "duplicate_start"
    assert body["alerts"][0]["severity"] == "medium"


async def test_movement_continuity_mismatch_creates_alert(
    client: AsyncClient,
    patient: dict,
) -> None:
    endpoint = f"/api/v1/patients/{patient['id']}/movements"
    first = await client.post(
        endpoint,
        json={
            "from_location": "entrada-sintetica",
            "to_location": "ala-a-sintetica",
            "is_synthetic": True,
        },
    )
    second = await client.post(
        endpoint,
        json={
            "from_location": "ala-x-sintetica",
            "to_location": "ala-b-sintetica",
            "is_synthetic": True,
        },
    )

    assert first.status_code == 201
    assert first.json()["events"] == []
    assert second.status_code == 201
    body = second.json()
    anomaly_codes = {item["code"] for item in body["events"][0]["payload"]["anomalies"]}
    assert "location_continuity_mismatch" in anomaly_codes
    assert body["events"][0]["severity"] == "high"
    assert body["alerts"][0]["status"] == "open"

    listed = await client.get(endpoint)
    assert listed.status_code == 200
    assert len(listed.json()) == 2
