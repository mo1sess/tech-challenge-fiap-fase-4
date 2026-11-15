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
        "azure_ai_language",
        "azure_text_analytics_for_health",
        "numpy_pcm_wav",
    ]
    for endpoint, record in (("media", body["media"]), ("jobs", body["job"])):
        params = {"patient_id": patient["id"], "limit": 1}
        page = await client.get(f"/api/v1/{endpoint}", params=params)
        assert page.status_code == 200
        assert [item["id"] for item in page.json()] == [record["id"]]
        next_page = await client.get(f"/api/v1/{endpoint}", params={**params, "offset": 1})
        assert next_page.json() == []

    content = await client.get(f"/api/v1/media/{body['media']['id']}/content")
    assert content.status_code == 200
    assert content.content == synthetic_wav
    assert "consulta_ficticia.wav" in content.headers["content-disposition"]


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

