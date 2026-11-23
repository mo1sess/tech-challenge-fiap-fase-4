from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings

_TRANSCRIBERS = {
    "local": "faster_whisper_local",
    "azure": "azure_speech_to_text",
}


@dataclass(frozen=True)
class AudioProcessingPlan:
    media_path: Path
    transcriber: str = "azure_speech_to_text"
    text_analyzer: str = "deterministic_context_rules_v2"
    acoustic_analyzer: str = "numpy_pcm_wav"


def describe_pipeline(
    media_path: Path,
    settings: Settings | None = None,
) -> dict[str, object]:
    # Sem `settings`, mantém o rótulo legado (compatibilidade com chamadas e
    # testes existentes); com `settings`, o rótulo segue o provedor configurado.
    if settings is None:
        plan = AudioProcessingPlan(media_path=media_path)
    else:
        plan = AudioProcessingPlan(
            media_path=media_path,
            transcriber=_TRANSCRIBERS.get(
                settings.speech_provider, settings.speech_provider
            ),
        )
    return {
        "status": "ready",
        "media_path": str(plan.media_path),
        "components": [plan.transcriber, plan.text_analyzer, plan.acoustic_analyzer],
        "note": "Pipeline educacional da Etapa 3 pronto; nenhum diagnostico e produzido.",
    }

