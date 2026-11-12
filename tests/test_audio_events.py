
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


async def process_text(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
    text: str,
) -> dict:
    def fake_transcribe(*args, **kwargs):
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": text,
        }

    monkeypatch.setattr(
        "app.services.audio_flow.transcribe_wav",
        fake_transcribe,
    )

    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
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

    assert uploaded.status_code == 201

    job_id = uploaded.json()["job"]["id"]

    response = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert response.status_code == 200, response.text

    return response.json()


async def test_affirmed_help_creates_one_event(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    result = await process_text(
        client,
        patient,
        monkeypatch,
        "Preciso de ajuda.",
    )

    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == (
        "audio_help_request_review"
    )
    assert result["events"][0]["source"] == "audio_analysis"
    assert result["events"][0]["severity"] == "low"
    assert result["alerts"] == []

    event_id = result["events"][0]["id"]
    assert result["job"]["result"]["event_ids"] == [event_id]


async def test_negated_pain_does_not_create_event(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    result = await process_text(
        client,
        patient,
        monkeypatch,
        "Não estou com dor de cabeça.",
    )

    assert result["events"] == []
    assert result["alerts"] == []
    assert result["job"]["result"]["event_ids"] == []


async def test_duplicate_expressions_create_one_event(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    result = await process_text(
        client,
        patient,
        monkeypatch,
        "Estou com dor de cabeça.",
    )

    assert len(result["events"]) == 1

    event = result["events"][0]
    assert event["event_type"] == "audio_pain_report_review"

    findings = event["payload"]["findings"]
    assert len(findings) == 2


async def test_mixed_context_only_creates_help_event(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    result = await process_text(
        client,
        patient,
        monkeypatch,
        "Não estou com dor de cabeça, eu preciso de ajuda.",
    )

    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == (
        "audio_help_request_review"
    )


async def test_event_is_persisted(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    result = await process_text(
        client,
        patient,
        monkeypatch,
        "Preciso de ajuda.",
    )

    event_id = result["events"][0]["id"]

    response = await client.get(
        f"/api/v1/events?patient_id={patient['id']}"
    )

    assert response.status_code == 200
    assert any(
        event["id"] == event_id
        for event in response.json()
    )
