from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoProcessingPlan:
    media_path: Path
    frame_reader: str = "opencv"
    pose_analyzer: str = "mediapipe_or_openpose"
    object_detector: str = "yolov8_optional"


def describe_pipeline(media_path: Path) -> dict[str, object]:
    plan = VideoProcessingPlan(media_path=media_path)
    return {
        "status": "prepared_not_executed",
        "media_path": str(plan.media_path),
        "components": [plan.frame_reader, plan.pose_analyzer, plan.object_detector],
        "note": "Implementacao analitica prevista para a Etapa 2; nenhum diagnostico e produzido aqui.",
    }

