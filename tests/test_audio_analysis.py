
import io
import wave

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


def create_synthetic_wav() -> bytes:
    """Generate a valid 1-second synthetic WAV file."""
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)

        # One second of silence, 16-bit PCM mono
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


async def test_audio_job_transcribes_and_persists_result(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the complete audio processing workflow."""

    def fake_transcribe(*args, **kwargs):
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": "Estou sentindo dor de cabeca.",
        }

    # Mock Azure Speech to avoid external API calls.
    monkeypatch.setattr(
        "app.services.audio_flow.transcribe_wav",
        fake_transcribe,
    )

    # 1. Upload synthetic audio
    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={
            "file": (
                "synthetic.wav",
                create_synthetic_wav(),
                "audio/wav",
            )
        },
        data={
            "kind": "audio",
            "is_synthetic": "true",
        },
    )

    assert uploaded.status_code == 201, uploaded.text

    upload_body = uploaded.json()

    assert upload_body["media"]["kind"] == "audio"
    assert upload_body["job"]["job_type"] == "audio_analysis"
    assert upload_body["job"]["status"] == "queued"

    job_id = upload_body["job"]["id"]

    # 2. Process the audio job
    processed = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert processed.status_code == 200, processed.text

    body = processed.json()
    job = body["job"]
    analysis = job["result"]["analysis"]

    assert job["status"] == "completed"
    assert job["progress"] == 100.0
    assert job["error"] is None

    # 3. Validate Azure Speech transcription
    transcription = analysis["transcription"]

    assert transcription["provider"] == "azure_speech"
    assert transcription["language"] == "pt-BR"
    assert transcription["status"] == "recognized"
    assert transcription["text"] == (
        "Estou sentindo dor de cabeca."
    )

    # 4. Validate acoustic analysis
    acoustic = analysis["acoustic"]

    assert acoustic["duration_seconds"] == pytest.approx(1.0)
    assert acoustic["sample_rate"] == 16000
    assert acoustic["channels"] == 1
    assert acoustic["rms"] == pytest.approx(0.0)
    assert acoustic["peak_amplitude"] == pytest.approx(0.0)
    assert acoustic["silence_ratio"] == pytest.approx(1.0)
    assert acoustic["clipping_ratio"] == pytest.approx(0.0)

    # 5. Validate contextual text analysis
    text_analysis = analysis["text_analysis"]

    assert text_analysis["analyzer"] == (
        "deterministic_context_rules_v2"
    )
    assert "pain_report" in text_analysis["matched_signals"]
    assert text_analysis["requires_review"] is True

    assert any(
        finding["signal"] == "pain_report"
        and finding["context"] == "affirmed"
        for finding in text_analysis["findings"]
    )

    # 6. Validate generated review event
    assert len(body["events"]) == 1

    event = body["events"][0]

    assert event["patient_id"] == patient["id"]
    assert event["source"] == "audio_analysis"
    assert event["event_type"] == "audio_pain_report_review"
    assert event["severity"] == "low"

    assert event["payload"]["signal"] == "pain_report"
    assert event["payload"]["context"] == "affirmed"
    assert event["payload"]["job_id"] == job_id
    assert event["payload"]["requires_human_review"] is True

    # One event for this signal, no automatic medical alerts.
    assert job["result"]["event_ids"] == [event["id"]]
    assert job["result"]["alert_ids"] == []
    assert body["alerts"] == []

    # 7. Verify persistence through the jobs endpoint
    persisted = await client.get(
        f"/api/v1/jobs/{job_id}"
    )

    assert persisted.status_code == 200

    persisted_job = persisted.json()

    assert persisted_job["job_type"] == "audio_analysis"
    assert persisted_job["status"] == "completed"

    assert (
        persisted_job["result"]["analysis"]["transcription"]
        == transcription
    )

    assert (
        persisted_job["result"]["analysis"]["acoustic"]
        == acoustic
    )

    assert (
        persisted_job["result"]["analysis"]["text_analysis"]
        == text_analysis
    )

    assert persisted_job["result"]["event_ids"] == [event["id"]]

    # 8. Verify event persistence through clinical events endpoint
    events_response = await client.get(
        f"/api/v1/events?patient_id={patient['id']}"
    )

    assert events_response.status_code == 200

    persisted_events = events_response.json()

    assert any(
        item["id"] == event["id"]
        and item["event_type"] == "audio_pain_report_review"
        for item in persisted_events
    )

    # 9. Verify completed jobs cannot be processed twice
    repeated = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert repeated.status_code == 409

    # 10. Verify no duplicate events were created
    events_after_retry = await client.get(
        f"/api/v1/events?patient_id={patient['id']}"
    )

    assert events_after_retry.status_code == 200

    matching_events = [
        item
        for item in events_after_retry.json()
        if item["id"] == event["id"]
    ]

    assert len(matching_events) == 1
