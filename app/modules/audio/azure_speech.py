
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk

from app.core.config import Settings


class AudioTranscriptionError(Exception):
    """Erro durante a transcrição de áudio."""


def transcribe_wav(
    audio_path: Path,
    settings: Settings,
) -> dict[str, object]:
    if audio_path.suffix.lower() != ".wav":
        raise AudioTranscriptionError(
            "Esta versão do adaptador aceita apenas WAV."
        )

    if not audio_path.is_file():
        raise AudioTranscriptionError(
            f"Arquivo não encontrado: {audio_path}"
        )

    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise AudioTranscriptionError(
            "Credenciais do Azure Speech não configuradas."
        )

    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )
    speech_config.speech_recognition_language = "pt-BR"

    audio_config = speechsdk.audio.AudioConfig(
        filename=str(audio_path.resolve())
    )

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "recognized",
            "text": result.text,
        }

    if result.reason == speechsdk.ResultReason.NoMatch:
        return {
            "provider": "azure_speech",
            "language": "pt-BR",
            "status": "no_match",
            "text": "",
        }

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise AudioTranscriptionError(
            f"Azure Speech cancelou a transcrição: "
            f"{details.reason} - {details.error_details}"
        )

    raise AudioTranscriptionError(
        f"Resultado inesperado do Azure Speech: {result.reason}"
    )
