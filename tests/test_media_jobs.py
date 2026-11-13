import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


async def test_audio_upload_creates_queued_job(client: AsyncClient, patient: dict) -> None:
    synthetic_wav = b"RIFF" + b"\x00" * 64
    response = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("consulta_ficticia.wav", synthetic_wav, "audio/wav")},
        data={"is_synthetic": "true"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["media"]["kind"] == "audio"
    assert body["job"]["status"] == "queued"
    assert body["job"]["result"]["pipeline"]["status"] == "ready"
    assert body["job"]["result"]["pipeline"]["components"] == [
        "azure_speech_to_text",
        "deterministic_context_rules_v2",
        "numpy_pcm_wav",
    ]


async def test_rejects_audio_format_not_supported_by_processor(
    client: AsyncClient,
    patient: dict,
) -> None:
    response = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("audio_sintetico.mp3", b"synthetic", "audio/mpeg")},
        data={"is_synthetic": "true"},
    )

    assert response.status_code == 415

