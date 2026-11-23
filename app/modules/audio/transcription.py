from pathlib import Path

from app.core.config import Settings


class AudioTranscriptionError(Exception):
    """Erro durante a transcrição de áudio."""


def transcribe_wav(
    audio_path: Path,
    settings: Settings,
) -> dict[str, object]:
    """Valida o WAV e despacha para o provedor em `settings.speech_provider`."""
    if audio_path.suffix.lower() != ".wav":
        raise AudioTranscriptionError(
            "Esta versão do adaptador aceita apenas WAV."
        )

    if not audio_path.is_file():
        raise AudioTranscriptionError(
            f"Arquivo não encontrado: {audio_path}"
        )

    provider = settings.speech_provider

    if provider == "local":
        from app.modules.audio.local_speech import transcribe_local

        return transcribe_local(audio_path, settings)

    if provider == "azure":
        from app.modules.audio.azure_speech import transcribe_azure

        return transcribe_azure(audio_path, settings)

    raise AudioTranscriptionError(
        f"Provedor de transcrição desconhecido: {provider}"
    )
