
import io
import wave
from unittest.mock import MagicMock, Mock

import pytest
from azure.ai.textanalytics import (
    AnalyzeHealthcareEntitiesResult,
    AnalyzeSentimentResult,
    HealthcareEntity,
    SentimentConfidenceScores,
)
from azure.core.exceptions import ServiceRequestError
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import ProcessingJob
from app.services.audio_flow import process_audio_job

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
    assert analysis["sentiment_analysis"]["status"] == "unavailable"
    assert analysis["sentiment_analysis"]["reason"] == "missing_configuration"
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


@pytest.mark.parametrize(
    ("transcription_status", "text", "scenario", "status", "reason", "signals"),
    [
        ("recognized", "O passeio foi horrível.", "negative", "succeeded", None, []),
        ("recognized", "Estou com dor.", "offline", "unavailable", "service_error", ["pain_report"]),
        ("recognized", "Estou com dor.", "healthcare-offline", "succeeded", None, ["pain_report"]),
        ("recognized", "Estou com dor.", "unconfigured", "unavailable", "missing_configuration", ["pain_report"]),
        ("recognized", " ", "negative", "skipped", "empty_text", []),
        ("no_match", "", "negative", "skipped", "speech_not_recognized", []),
    ],
)
async def test_audio_sentiment_is_persisted_independently(
    client: AsyncClient,
    patient: dict,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    transcription_status: str,
    text: str,
    scenario: str,
    status: str,
    reason: str | None,
    signals: list[str],
) -> None:
    transcription = {
        "provider": "azure_speech",
        "language": "pt-BR",
        "status": transcription_status,
        "text": text,
    }
    monkeypatch.setattr("app.services.audio_flow.transcribe_wav", Mock(return_value=transcription))

    client_class = MagicMock()
    azure_client = client_class.return_value.__enter__.return_value
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", client_class)
    healthcare_class = MagicMock()
    monkeypatch.setattr("app.modules.audio.azure_healthcare.TextAnalyticsClient", healthcare_class)
    healthcare_client = healthcare_class.return_value.__aenter__.return_value
    healthcare_operation = healthcare_client.begin_analyze_healthcare_entities

    async def healthcare_results():
        entities = [
            HealthcareEntity(text="dor", category="SymptomOrSign", offset=10, length=3, confidence_score=0.9)
        ] if signals else []
        yield AnalyzeHealthcareEntitiesResult(entities=entities)

    healthcare_operation.return_value.result.return_value = healthcare_results()
    if scenario == "healthcare-offline":
        healthcare_operation.side_effect = ServiceRequestError("private failure detail")
    if scenario != "unconfigured":
        test_settings.azure_language_endpoint = "https://language.example.invalid"
        test_settings.azure_language_key = "dummy-key"
    if scenario == "offline":
        azure_client.analyze_sentiment.side_effect = ServiceRequestError("private failure detail")
    else:
        azure_client.analyze_sentiment.return_value = [
            AnalyzeSentimentResult(
                id="0",
                sentiment="negative",
                confidence_scores=SentimentConfidenceScores(positive=0.01, neutral=0.04, negative=0.95),
                sentences=[],
                warnings=[],
            ),
        ]

    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("synthetic.wav", create_synthetic_wav(), "audio/wav")},
        data={"is_synthetic": "true"},
    )
    assert uploaded.status_code == 201
    job_id = uploaded.json()["job"]["id"]

    processed = await client.post(f"/api/v1/jobs/{job_id}/process")
    assert processed.status_code == 200
    body = processed.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["progress"] == 100.0
    assert body["job"]["error"] is None
    assert len(body["events"]) == len(signals)
    assert body["job"]["result"]["alert_ids"] == []
    assert body["alerts"] == []

    analysis = body["job"]["result"]["analysis"]
    assert analysis["transcription"] == transcription
    assert analysis["acoustic"]["duration_seconds"] == 1.0
    assert analysis["text_analysis"]["matched_signals"] == signals
    assert analysis["text_analysis"]["requires_review"] == bool(signals)
    mentions = analysis["clinical_mentions"]
    if scenario == "healthcare-offline":
        assert mentions["status"] == "unavailable"
        assert mentions["reason"] == "service_error"
    elif status == "skipped" or scenario == "unconfigured":
        assert mentions["status"] == status
        assert mentions["reason"] == reason
        healthcare_class.assert_not_called()
    else:
        assert mentions["status"] == "succeeded"
        assert [mention["text"] for mention in mentions["mentions"]] == (["dor"] if signals else [])
    sentiment = analysis["sentiment_analysis"]
    assert sentiment["status"] == status
    assert sentiment.get("reason") == reason
    if status == "succeeded":
        assert sentiment["sentiment"] == "negative"
        assert sentiment["confidence_scores"]["negative"] == 0.95
        alerts = await client.get(f"/api/v1/alerts?patient_id={patient['id']}")
        assert alerts.status_code == 200
        assert alerts.json() == []
    else:
        assert "sentiment" not in sentiment
    if status == "succeeded" or reason == "service_error":
        azure_client.analyze_sentiment.assert_called_once_with(
            [text], language="pt-BR", disable_service_logs=True
        )
    else:
        client_class.assert_not_called()
    assert "private failure detail" not in processed.text

    persisted = await client.get(f"/api/v1/jobs/{job_id}")
    assert persisted.status_code == 200
    assert persisted.json()["job_type"] == "audio_analysis"
    assert persisted.json()["result"]["analysis"] == analysis

    repeated = await client.post(f"/api/v1/jobs/{job_id}/process")
    assert repeated.status_code == 409


async def test_audio_job_rejects_a_claim_based_on_stale_status(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def finish_in_another_session(db, job, media, patient, settings):
        with Session(db.get_bind()) as concurrent_db:
            concurrent_job = concurrent_db.get(ProcessingJob, job.id)
            concurrent_job.status = "completed"
            concurrent_job.result = {"analysis": {"sentiment_analysis": {"status": "succeeded"}}}
            concurrent_db.commit()
        return process_audio_job(db, job, media, patient, settings)

    transcribe = Mock()
    monkeypatch.setattr("app.services.audio_flow.transcribe_wav", transcribe)
    monkeypatch.setattr("app.api.routes.media.process_audio_job", finish_in_another_session)
    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("synthetic.wav", create_synthetic_wav(), "audio/wav")},
        data={"is_synthetic": "true"},
    )
    assert uploaded.status_code == 201
    job_id = uploaded.json()["job"]["id"]

    rejected = await client.post(f"/api/v1/jobs/{job_id}/process")

    assert rejected.status_code == 409
    transcribe.assert_not_called()
    persisted = (await client.get(f"/api/v1/jobs/{job_id}")).json()
    assert persisted["status"] == "completed"
    assert persisted["result"]["analysis"]["sentiment_analysis"]["status"] == "succeeded"
