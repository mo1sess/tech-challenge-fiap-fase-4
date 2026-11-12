from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioProcessingPlan:
    media_path: Path
    transcriber: str = "azure_speech_to_text"
    text_analyzer: str = "deterministic_context_rules_v2"
    acoustic_analyzer: str = "numpy_pcm_wav"


def describe_pipeline(media_path: Path) -> dict[str, object]:
    plan = AudioProcessingPlan(media_path=media_path)
    return {
        "status": "ready",
        "media_path": str(plan.media_path),
        "components": [plan.transcriber, plan.text_analyzer, plan.acoustic_analyzer],
        "note": "Pipeline educacional da Etapa 3 pronto; nenhum diagnostico e produzido.",
    }

