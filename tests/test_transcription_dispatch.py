import io
import wave

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.audio import transcription
from app.modules.audio.processor import describe_pipeline
from app.modules.audio.transcription import (
    AudioTranscriptionError,
    transcribe_wav,
)

pytestmark = pytest.mark.anyio

SPEECH_ENV_VARS = (
    "SPEECH_PROVIDER",
    "WHISPER_MODEL_SIZE",
    "WHISPER_DEVICE",
    "WHISPER_COMPUTE_TYPE",
    "WHISPER_MODEL_DIR",
)


def synthetic_wav() -> bytes:
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000)

    return buffer.getvalue()


def fake_result(provider: str) -> dict[str, object]:
    return {
        "provider": provider,
        "language": "pt-BR",
        "status": "recognized",
        "text": "texto de teste",
    }


# --- Despachante: validação de entrada -------------------------------------


def test_mp3_file_is_rejected_as_not_wav(tmp_path):
    mp3 = tmp_path / "audio.mp3"
    mp3.write_bytes(b"ID3 fake")

    with pytest.raises(AudioTranscriptionError, match="apenas WAV"):
        transcribe_wav(mp3, Settings(_env_file=None))


def test_missing_wav_file_is_rejected(tmp_path):
    missing = tmp_path / "inexistente.wav"

    with pytest.raises(AudioTranscriptionError, match="não encontrado"):
        transcribe_wav(missing, Settings(_env_file=None))


# --- Despachante: roteamento por speech_provider ---------------------------


def test_provider_local_dispatches_to_transcribe_local(tmp_path, monkeypatch):
    wav = tmp_path / "entrada.wav"
    wav.write_bytes(synthetic_wav())

    calls = {"local": 0, "azure": 0}

    def fake_local(audio_path, settings):
        calls["local"] += 1
        return fake_result("faster_whisper")

    def fake_azure(audio_path, settings):
        calls["azure"] += 1
        return fake_result("azure_speech")

    monkeypatch.setattr(
        "app.modules.audio.local_speech.transcribe_local", fake_local
    )
    monkeypatch.setattr(
        "app.modules.audio.azure_speech.transcribe_azure", fake_azure
    )

    result = transcribe_wav(
        wav, Settings(speech_provider="local", _env_file=None)
    )

    assert result == fake_result("faster_whisper")
    assert calls == {"local": 1, "azure": 0}


def test_provider_azure_dispatches_to_transcribe_azure(tmp_path, monkeypatch):
    wav = tmp_path / "entrada.wav"
    wav.write_bytes(synthetic_wav())

    calls = {"local": 0, "azure": 0}

    def fake_local(audio_path, settings):
        calls["local"] += 1
        return fake_result("faster_whisper")

    def fake_azure(audio_path, settings):
        calls["azure"] += 1
        return fake_result("azure_speech")

    monkeypatch.setattr(
        "app.modules.audio.local_speech.transcribe_local", fake_local
    )
    monkeypatch.setattr(
        "app.modules.audio.azure_speech.transcribe_azure", fake_azure
    )

    result = transcribe_wav(
        wav, Settings(speech_provider="azure", _env_file=None)
    )

    assert result == fake_result("azure_speech")
    assert calls == {"local": 0, "azure": 1}


# --- Settings: padrões e validação -----------------------------------------


def test_settings_defaults_without_env(monkeypatch):
    for name in SPEECH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.speech_provider == "local"
    assert settings.whisper_model_size == "base"
    assert settings.whisper_device == "cpu"
    assert settings.whisper_compute_type == "int8"
    assert settings.whisper_model_dir is None


def test_settings_rejects_unknown_speech_provider():
    with pytest.raises(ValidationError):
        Settings(speech_provider="outro", _env_file=None)


def test_adapter_error_class_is_shared_with_transcription_module():
    from app.modules.audio.azure_speech import (
        AudioTranscriptionError as AzureError,
    )

    assert AzureError is transcription.AudioTranscriptionError


# --- Pipeline: rótulo do transcritor ---------------------------------------


def test_describe_pipeline_without_settings_keeps_legacy_label(tmp_path):
    components = describe_pipeline(tmp_path / "a.wav")["components"]

    assert "azure_speech_to_text" in components


def test_describe_pipeline_with_local_provider_label(tmp_path):
    result = describe_pipeline(
        tmp_path / "a.wav",
        Settings(speech_provider="local", _env_file=None),
    )

    assert "faster_whisper_local" in result["components"]


def test_describe_pipeline_with_azure_provider_label(tmp_path):
    result = describe_pipeline(
        tmp_path / "a.wav",
        Settings(speech_provider="azure", _env_file=None),
    )

    assert "azure_speech_to_text" in result["components"]


# --- Integração pela API: despachante real com adaptador local mockado -----


async def test_api_audio_job_uses_local_provider_without_azure(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    for name in (
        "AZURE_SPEECH_KEY",
        "AZURE_SPEECH_REGION",
        "SPEECH_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)

    def fake_transcribe_local(audio_path, settings):
        return {
            "provider": "faster_whisper",
            "model": "base",
            "language": "pt-BR",
            "status": "recognized",
            "text": "preciso de ajuda",
        }

    monkeypatch.setattr(
        "app.modules.audio.local_speech.transcribe_local",
        fake_transcribe_local,
    )

    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("synthetic.wav", synthetic_wav(), "audio/wav")},
        data={"kind": "audio", "is_synthetic": "true"},
    )

    assert uploaded.status_code == 201

    job_id = uploaded.json()["job"]["id"]

    response = await client.post(f"/api/v1/jobs/{job_id}/process")

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["job"]["status"] == "completed"
    transcription_result = body["job"]["result"]["analysis"]["transcription"]
    assert transcription_result["provider"] == "faster_whisper"
    assert len(body["events"]) >= 1
