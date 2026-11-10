
import io
import wave

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


def create_synthetic_wav() -> bytes:
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)

        # One second of synthetic silence in 16-bit PCM
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


async def test_audio_job_transcribes_and_persists_result(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_transcribe(*args, **kwargs):
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": "Estou sentindo dor de cabeca.",
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
        create_synthetic_wav(),
        "audio/wav",
    )
},
        data={"is_synthetic": "true"},
    )

    assert uploaded.status_code == 201

    job_id = uploaded.json()["job"]["id"]

    processed = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert processed.status_code == 200

    body = processed.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["progress"] == 100.0

    transcription = body["job"]["result"]["analysis"]["transcription"]

    assert transcription["status"] == "recognized"
    assert transcription["text"] == "Estou sentindo dor de cabeca."
    assert body["events"] == []
    assert body["alerts"] == []

    persisted = await client.get(
        f"/api/v1/jobs/{job_id}"
    )

    assert persisted.status_code == 200
    assert persisted.json()["job_type"] == "audio_analysis"
    assert persisted.json()["result"]["analysis"]["transcription"] == transcription

    repeated = await client.post(
        f"/api/v1/jobs/{job_id}/process"
    )

    assert repeated.status_code == 409
