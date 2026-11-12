
import io
import wave

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


def synthetic_wav() -> bytes:
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


async def create_audio_event(
    client: AsyncClient,
    patient_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    def fake_transcribe(*args, **kwargs):
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": "Preciso de ajuda.",
        }

    monkeypatch.setattr(
        "app.services.audio_flow.transcribe_wav",
        fake_transcribe,
    )

    uploaded = await client.post(
        f"/api/v1/patients/{patient_id}/media",
        files={
            "file": (
                "synthetic.wav",
                synthetic_wav(),
                "audio/wav",
            )
        },
        data={
            "kind": "audio",
            "is_synthetic": "true",
        },
    )

    assert uploaded.status_code == 201, uploaded.text

    job_id = uploaded.json()["job"]["id"]

    processed = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert processed.status_code == 200, processed.text
    assert len(processed.json()["events"]) == 1

    return processed.json()["events"][0]["id"]


async def create_vital_event(
    client: AsyncClient,
    patient_id: str,
    measured_at: str | None = None,
) -> str:
    payload = {
        "heart_rate_bpm": 145,
        "is_synthetic": True,
    }

    if measured_at is not None:
        payload["measured_at"] = measured_at

    response = await client.post(
        f"/api/v1/patients/{patient_id}/measurements",
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert len(response.json()["events"]) == 1

    return response.json()["events"][0]["id"]


async def test_audio_vital_correlation(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    audio_id = await create_audio_event(
        client,
        patient_id,
        monkeypatch,
    )

    vital_id = await create_vital_event(
        client,
        patient_id,
    )

    response = await client.post(
        f"/api/v1/patients/{patient_id}/correlations/run"
    )

    assert response.status_code == 200, response.text

    correlations = response.json()
    assert len(correlations) == 1

    event = correlations[0]

    assert event["source"] == "multimodal_correlation"
    assert event["event_type"] == (
        "synthetic_audio_vital_correlation"
    )
    assert event["severity"] == "low"

    assert event["payload"]["audio_event_id"] == audio_id
    assert event["payload"]["vital_event_id"] == vital_id

    assert (
        event["payload"]["correlation_type"]
        == "temporal_cooccurrence"
    )

    assert event["payload"]["requires_human_review"] is True

    # Verify persistence.
    events_response = await client.get(
        f"/api/v1/events?patient_id={patient_id}"
    )

    assert events_response.status_code == 200

    assert any(
        item["id"] == event["id"]
        for item in events_response.json()
    )


async def test_correlation_is_idempotent(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    await create_audio_event(
        client,
        patient_id,
        monkeypatch,
    )

    await create_vital_event(
        client,
        patient_id,
    )

    endpoint = (
        f"/api/v1/patients/{patient_id}/correlations/run"
    )

    first = await client.post(endpoint)
    second = await client.post(endpoint)

    assert first.status_code == 200
    assert second.status_code == 200

    assert len(first.json()) == 1
    assert second.json() == []


async def test_no_correlation_outside_time_window(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    patient_id = patient["id"]

    await create_audio_event(
        client,
        patient_id,
        monkeypatch,
    )

    # Historical synthetic measurement outside the window.
    await create_vital_event(
        client,
        patient_id,
        measured_at="2020-01-01T12:00:00Z",
    )

    response = await client.post(
        f"/api/v1/patients/{patient_id}/correlations/run"
        "?window_minutes=5"
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_correlation_requires_existing_patient(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/patients/nonexistent/correlations/run"
    )

    assert response.status_code == 404
