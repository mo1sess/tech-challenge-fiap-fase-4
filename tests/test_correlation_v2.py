
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from tests.test_correlation import create_audio_event, create_vital_event

pytestmark = pytest.mark.anyio


async def create_video_event(
    client: AsyncClient,
    patient_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    analysis = SimpleNamespace(
        anomalies=[
            {
                "code": "sustained_low_motion",
                "severity": "high",
                "title": "Baixa variacao de movimento",
                "description": "Anomalia sintetica de teste",
                "observed_value": 0.1,
                "threshold": 0.35,
                "unit": "percent_changed_pixels",
            }
        ],
        to_dict=lambda: {
            "decoder": "opencv_mock",
            "anomalies": ["sustained_low_motion"],
        },
    )

    monkeypatch.setattr(
        "app.services.video_flow.analyze_video",
        lambda *args, **kwargs: analysis,
    )

    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/media",
        files={
            "file": (
                "synthetic.avi",
                b"synthetic-video-test-data",
                "video/x-msvideo",
            )
        },
        data={
            "kind": "video",
            "is_synthetic": "true",
        },
    )

    assert uploaded.status_code == 201, uploaded.text

    job_id = uploaded.json()["job"]["id"]

    processed = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert processed.status_code == 200, processed.text

    events = processed.json()["events"]
    assert len(events) == 1

    return events[0]["id"]


async def run_v2(
    client: AsyncClient,
    patient_id: str,
    window_minutes: int = 5,
):
    return await client.post(
        f"/api/v1/patients/{patient_id}/correlations/run-v2",
        params={"window_minutes": window_minutes},
    )


async def test_audio_video_correlation(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    audio_id = await create_audio_event(
        client, patient_id, monkeypatch
    )
    video_id = await create_video_event(
        client, patient_id, monkeypatch
    )

    response = await run_v2(client, patient_id)
    assert response.status_code == 200, response.text

    events = response.json()
    assert len(events) == 1

    payload = events[0]["payload"]
    assert payload["source_count"] == 2
    assert set(payload["source_event_ids"]) == {
        audio_id, video_id
    }
    assert payload["sources"] == ["audio", "video"]


async def test_video_vital_correlation(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    video_id = await create_video_event(
        client, patient_id, monkeypatch
    )
    vital_id = await create_vital_event(
        client, patient_id
    )

    response = await run_v2(client, patient_id)
    assert response.status_code == 200, response.text

    events = response.json()
    assert len(events) == 1

    payload = events[0]["payload"]
    assert payload["source_count"] == 2
    assert set(payload["source_event_ids"]) == {
        video_id, vital_id
    }
    assert payload["sources"] == ["video", "vital"]


async def test_three_source_correlation(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    audio_id = await create_audio_event(
        client, patient_id, monkeypatch
    )
    video_id = await create_video_event(
        client, patient_id, monkeypatch
    )
    vital_id = await create_vital_event(
        client, patient_id
    )

    response = await run_v2(client, patient_id)
    assert response.status_code == 200, response.text

    events = response.json()

    # Triple takes priority over overlapping video pairs.
    assert len(events) == 1

    payload = events[0]["payload"]

    assert payload["source_count"] == 3
    assert payload["sources"] == [
        "audio", "video", "vital"
    ]
    assert set(payload["source_event_ids"]) == {
        audio_id, video_id, vital_id
    }
    assert payload["time_span_seconds"] <= 300

    # Verify idempotency.
    repeated = await run_v2(client, patient_id)
    assert repeated.status_code == 200
    assert repeated.json() == []


async def test_no_correlation_with_old_vital_event(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    await create_video_event(
        client, patient_id, monkeypatch
    )
    await create_vital_event(
        client,
        patient_id,
        measured_at="2020-01-01T12:00:00Z",
    )

    response = await run_v2(client, patient_id)
    assert response.status_code == 200
    assert response.json() == []


async def test_different_patients_are_not_correlated(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    second = await client.post(
        "/api/v1/patients",
        json={
            "code": "MG-TEST-002",
            "alias": "Segundo Paciente Sintetico",
            "birth_year": 1995,
            "is_synthetic": True,
        },
    )
    assert second.status_code == 201

    await create_audio_event(
        client, patient["id"], monkeypatch
    )
    await create_video_event(
        client, second.json()["id"], monkeypatch
    )

    response = await run_v2(client, patient["id"])
    assert response.status_code == 200
    assert response.json() == []
