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
    assert body["job"]["result"]["pipeline"]["status"] == "prepared_not_executed"

