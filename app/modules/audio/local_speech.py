from functools import lru_cache
from pathlib import Path

from app.core.config import Settings
from app.modules.audio.transcription import AudioTranscriptionError


@lru_cache(maxsize=4)
def _load_model(
    size: str,
    device: str,
    compute_type: str,
    download_root: str | None,
):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise AudioTranscriptionError(
            "faster-whisper não está instalado. "
            "Instale com: pip install faster-whisper"
        ) from exc

    try:
        return WhisperModel(
            size,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
    except Exception as exc:
        raise AudioTranscriptionError(
            f"Falha ao carregar o modelo Whisper '{size}': {exc}"
        ) from exc


def transcribe_local(
    audio_path: Path,
    settings: Settings,
) -> dict[str, object]:
    """Transcreve o WAV localmente com faster-whisper (pt-BR)."""
    model_dir = (
        str(settings.whisper_model_dir) if settings.whisper_model_dir else None
    )
    model = _load_model(
        settings.whisper_model_size,
        settings.whisper_device,
        settings.whisper_compute_type,
        model_dir,
    )

    try:
        segments, _info = model.transcribe(
            str(audio_path.resolve()),
            language="pt",
        )
        text = " ".join(
            segment.text.strip() for segment in segments if segment.text.strip()
        ).strip()
    except Exception as exc:
        raise AudioTranscriptionError(
            f"Falha na transcrição local com faster-whisper: {exc}"
        ) from exc

    return {
        "provider": "faster_whisper",
        "model": settings.whisper_model_size,
        "language": "pt-BR",
        "status": "recognized" if text else "no_match",
        "text": text,
    }
