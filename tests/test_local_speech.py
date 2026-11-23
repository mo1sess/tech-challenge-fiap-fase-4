import sys
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.modules.audio import local_speech
from app.modules.audio.local_speech import _load_model, transcribe_local
from app.modules.audio.transcription import AudioTranscriptionError


@pytest.fixture(autouse=True)
def isolate_speech_env(monkeypatch):
    # O docker-compose define WHISPER_MODEL_DIR etc.; os testes usam os defaults.
    for name in (
        "SPEECH_PROVIDER",
        "WHISPER_MODEL_SIZE",
        "WHISPER_DEVICE",
        "WHISPER_COMPUTE_TYPE",
        "WHISPER_MODEL_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def clear_model_cache():
    _load_model.cache_clear()
    yield
    _load_model.cache_clear()


class FakeWhisperModel:
    instances: list["FakeWhisperModel"] = []
    segments: list[str] = []
    transcribe_error: Exception | None = None
    constructor_error: Exception | None = None

    def __init__(self, size, device="cpu", compute_type="int8", download_root=None):
        if FakeWhisperModel.constructor_error is not None:
            raise FakeWhisperModel.constructor_error
        self.size = size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self.transcribe_calls: list[dict] = []
        FakeWhisperModel.instances.append(self)

    def transcribe(self, path, language=None):
        self.transcribe_calls.append({"path": path, "language": language})
        if FakeWhisperModel.transcribe_error is not None:
            raise FakeWhisperModel.transcribe_error
        segments = [SimpleNamespace(text=text) for text in FakeWhisperModel.segments]
        return segments, SimpleNamespace(language="pt")


@pytest.fixture
def fake_faster_whisper(monkeypatch):
    FakeWhisperModel.instances = []
    FakeWhisperModel.segments = []
    FakeWhisperModel.transcribe_error = None
    FakeWhisperModel.constructor_error = None

    fake_module = SimpleNamespace(WhisperModel=FakeWhisperModel)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    return FakeWhisperModel


@pytest.fixture
def wav_file(tmp_path):
    path = tmp_path / "entrada.wav"
    path.write_bytes(b"RIFF fake wav")
    return path


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


# --- Adaptador: transcrição com modelo mockado -----------------------------


def test_transcribe_joins_non_empty_segments(fake_faster_whisper, wav_file):
    fake_faster_whisper.segments = [
        " Estou com dor ",
        "  ",
        "preciso de ajuda",
    ]

    result = transcribe_local(wav_file, make_settings())

    assert result["text"] == "Estou com dor preciso de ajuda"
    assert result["status"] == "recognized"
    assert result["provider"] == "faster_whisper"
    assert result["model"] == "base"
    assert result["language"] == "pt-BR"

    model = fake_faster_whisper.instances[0]
    assert model.transcribe_calls[0]["language"] == "pt"


def test_transcribe_with_no_segments_returns_no_match(
    fake_faster_whisper, wav_file
):
    fake_faster_whisper.segments = []

    result = transcribe_local(wav_file, make_settings())

    assert result["status"] == "no_match"
    assert result["text"] == ""


def test_whisper_model_receives_default_arguments(fake_faster_whisper, wav_file):
    transcribe_local(wav_file, make_settings())

    model = fake_faster_whisper.instances[0]
    assert model.size == "base"
    assert model.device == "cpu"
    assert model.compute_type == "int8"
    assert model.download_root is None


def test_whisper_model_dir_is_passed_as_download_root(
    fake_faster_whisper, wav_file, tmp_path
):
    transcribe_local(wav_file, make_settings(whisper_model_dir=tmp_path))

    model = fake_faster_whisper.instances[0]
    assert model.download_root == str(tmp_path)


def test_same_config_reuses_cached_model(fake_faster_whisper, wav_file):
    settings = make_settings()

    transcribe_local(wav_file, settings)
    transcribe_local(wav_file, settings)

    assert len(fake_faster_whisper.instances) == 1


# --- Adaptador: falhas mapeadas para AudioTranscriptionError ---------------


def test_missing_faster_whisper_package_raises_clear_error(
    monkeypatch, wav_file
):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)

    with pytest.raises(AudioTranscriptionError, match="faster-whisper"):
        transcribe_local(wav_file, make_settings())


def test_model_constructor_failure_raises_load_error(
    fake_faster_whisper, wav_file
):
    fake_faster_whisper.constructor_error = RuntimeError("modelo corrompido")

    with pytest.raises(AudioTranscriptionError, match="Falha ao carregar"):
        transcribe_local(wav_file, make_settings())


def test_transcribe_failure_raises_transcription_error(
    fake_faster_whisper, wav_file
):
    fake_faster_whisper.transcribe_error = RuntimeError("áudio ilegível")

    with pytest.raises(
        AudioTranscriptionError, match="Falha na transcrição local"
    ):
        transcribe_local(wav_file, make_settings())


def test_local_speech_module_exposes_expected_entrypoints():
    assert callable(local_speech.transcribe_local)
    assert callable(local_speech._load_model)
