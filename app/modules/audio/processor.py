from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioProcessingPlan:
    media_path: Path
    transcriber: str = "azure_speech_to_text"
    text_analyzer: str = "azure_ai_language"
    acoustic_analyzer: str = "librosa"


def describe_pipeline(media_path: Path) -> dict[str, object]:
    plan = AudioProcessingPlan(media_path=media_path)
    return {
        "status": "prepared_not_executed",
        "media_path": str(plan.media_path),
        "components": [plan.transcriber, plan.text_analyzer, plan.acoustic_analyzer],
        "note": "Implementacao analitica prevista para a Etapa 3; nenhum diagnostico e produzido aqui.",
    }

