
import io
import wave

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


def create_synthetic_wav() -> bytes:
    """Gera um WAV sintético válido com duração de um segundo."""
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)

        # Um segundo de silêncio em PCM mono de 16 bits.
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


async def test_audio_job_transcribes_and_persists_result(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida o fluxo completo de processamento de áudio."""

    def fake_transcribe(*args, **kwargs):
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": "Estou sentindo dor de cabeca.",
        }

    # Simula o Azure Speech para evitar chamadas à API externa.
    monkeypatch.setattr(
        "app.services.audio_flow.transcribe_wav",
        fake_transcribe,
    )

    # 1. Envia o áudio sintético.
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

    # 2. Processa a tarefa de áudio.
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

    # 3. Valida a transcrição do Azure Speech.
    transcription = analysis["transcription"]

    assert transcription["provider"] == "azure_speech"
    assert transcription["language"] == "pt-BR"
    assert transcription["status"] == "recognized"
    assert transcription["text"] == (
        "Estou sentindo dor de cabeca."
    )

    # 4. Valida a análise acústica.
    acoustic = analysis["acoustic"]

    assert acoustic["duration_seconds"] == pytest.approx(1.0)
    assert acoustic["sample_rate"] == 16000
    assert acoustic["channels"] == 1
    assert acoustic["rms"] == pytest.approx(0.0)
    assert acoustic["peak_amplitude"] == pytest.approx(0.0)
    assert acoustic["silence_ratio"] == pytest.approx(1.0)
    assert acoustic["clipping_ratio"] == pytest.approx(0.0)

    # 5. Valida a análise textual contextual.
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

    # 6. Valida o evento de revisão gerado.
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

    # Um evento para este sinal, sem alertas médicos automáticos.
    assert job["result"]["event_ids"] == [event["id"]]
    assert job["result"]["alert_ids"] == []
    assert body["alerts"] == []

    # 7. Verifica a persistência pela rota de tarefas.
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

    # 8. Verifica a persistência pela rota de eventos clínicos.
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

    # 9. Verifica o bloqueio de reprocessamento de tarefas concluídas.
    repeated = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert repeated.status_code == 409

    # 10. Verifica a ausência de eventos duplicados.
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
