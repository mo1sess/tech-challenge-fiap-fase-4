from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import ceil, isfinite
from pathlib import Path
from statistics import fmean
from typing import Any

try:
    import cv2
    import numpy as np
except ModuleNotFoundError:  # Allows the API to explain a missing video extra at runtime.
    cv2 = None
    np = None


DISCLAIMER = (
    "Analise educacional de video sintetico. Os resultados descrevem variacao visual, "
    "nao representam avaliacao clinica e nao devem orientar cuidados de saude."
)
def _interval(first_frame: int, last_frame: int, fps: float) -> dict[str, int | float | None]:
    return {
        "first_frame": first_frame,
        "last_frame": last_frame,
        "start_seconds": round(first_frame / fps, 3) if fps else None,
        "end_seconds": round(last_frame / fps, 3) if fps else None,
    }


class VideoProcessingError(RuntimeError):
    """Raised when a video cannot be decoded or analyzed safely."""


def _require_opencv() -> None:
    if cv2 is None or np is None:
        raise VideoProcessingError(
            "OpenCV video dependencies are unavailable. Install the project dependencies before processing video."
        )


@dataclass(frozen=True)
class VideoAnomaly:
    code: str
    severity: str
    title: str
    description: str
    observed_value: float
    threshold: float
    unit: str = "percent_changed_pixels"
    intervals: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class VideoAnalysis:
    decoder: str
    width: int
    height: int
    fps: float
    duration_seconds: float
    source_frame_count: int
    analyzed_frame_count: int
    sample_every_n_frames: int
    mean_motion_percent: float
    peak_motion_percent: float
    activity_label: str
    anomalies: list[dict[str, Any]]
    disclaimer: str = DISCLAIMER
    coverage: dict[str, Any] | None = None
    pose_analysis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def describe_pipeline(media_path: Path) -> dict[str, object]:
    return {
        "status": "ready",
        "media_path": str(media_path),
        "components": [
            "opencv_frame_reader", "frame_difference_motion", "openpose_coco", "yolov8_pose",
            "event_alert_bridge", "automatic_report",
        ],
        "note": DISCLAIMER,
    }


def _activity_label(mean_motion: float, low_threshold: float, abrupt_threshold: float) -> str:
    if mean_motion <= low_threshold:
        return "very_low_motion"
    if mean_motion >= abrupt_threshold:
        return "high_motion"
    return "expected_demo_range"


def analyze_video(
    media_path: Path,
    *,
    sample_every_n_frames: int = 3,
    low_motion_threshold: float = 0.35,
    abrupt_motion_threshold: float = 20.0,
    max_frames: int = 900,
    pose_model_dir: Path | None = None,
) -> VideoAnalysis:
    """Analyze scene movement and estimate posture in selected frames."""
    _require_opencv()
    from app.modules.video.pose import POSE_MODELS, POSE_SAMPLE_LIMIT, TRUNK_DEVIATION_DEGREES, PoseAnalyzer

    if not media_path.exists():
        raise VideoProcessingError("Video file was not found")

    capture = cv2.VideoCapture(str(media_path))
    if not capture.isOpened():
        capture.release()
        raise VideoProcessingError("Video could not be decoded by OpenCV")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    fps = fps if isfinite(fps) and fps > 0 else 0.0
    source_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = source_frame_count / fps if fps > 0 else 0.0
    previous: np.ndarray | None = None
    motion_scores: list[float] = []
    analyzed_frames = 0
    frame_index = 0
    pose_analyzer = None
    pose_reason = "model_files_missing"
    pose_samples: list[dict[str, Any]] = []
    expected_samples = min(ceil(source_frame_count / sample_every_n_frames), max_frames)
    pose_stride = max(1, ceil(expected_samples / POSE_SAMPLE_LIMIT))

    try:
        if pose_model_dir is not None:
            try:
                pose_analyzer = PoseAnalyzer(pose_model_dir)
            except FileNotFoundError:
                pass
            except (cv2.error, OSError, ValueError):
                pose_reason = "model_load_failed"
        while analyzed_frames < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            current_index = frame_index
            frame_index += 1
            if current_index % sample_every_n_frames != 0:
                continue

            if (
                pose_analyzer is not None
                and analyzed_frames % pose_stride == 0
                and len(pose_samples) < POSE_SAMPLE_LIMIT
            ):
                try:
                    pose_samples.append({
                        "frame": current_index,
                        **pose_analyzer.evaluate(frame),
                    })
                except (cv2.error, ValueError):
                    pose_reason = "model_inference_failed"
                    pose_analyzer = None
                    pose_samples.clear()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            analyzed_frames += 1
            if previous is not None:
                delta = cv2.absdiff(previous, gray)
                changed = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                motion_scores.append(float(np.count_nonzero(changed) / changed.size * 100.0))
            previous = gray
    finally:
        capture.release()

    if analyzed_frames < 2 or not motion_scores:
        raise VideoProcessingError("Video needs at least two analyzable frames")

    mean_motion = float(fmean(motion_scores))
    peak_index, peak_motion = max(enumerate(motion_scores), key=lambda item: item[1])
    last_sample = (analyzed_frames - 1) * sample_every_n_frames
    anomalies: list[VideoAnomaly] = []
    if mean_motion <= low_motion_threshold:
        anomalies.append(
            VideoAnomaly(
                code="sustained_low_motion",
                severity="high",
                title="Baixa variacao de movimento no video sintetico",
                description="A variacao media entre quadros ficou abaixo do limite demonstrativo configurado.",
                observed_value=round(mean_motion, 4),
                threshold=low_motion_threshold,
                intervals=[_interval(0, last_sample, fps)],
            )
        )
    if peak_motion >= abrupt_motion_threshold:
        anomalies.append(
            VideoAnomaly(
                code="abrupt_visual_change",
                severity="high",
                title="Mudanca visual abrupta no video sintetico",
                description="Um intervalo apresentou variacao visual acima do limite demonstrativo configurado.",
                observed_value=round(peak_motion, 4),
                threshold=abrupt_motion_threshold,
                intervals=[_interval(
                    peak_index * sample_every_n_frames, (peak_index + 1) * sample_every_n_frames, fps
                )],
            )
        )
    confirmed = [sample for sample in pose_samples if sample["status"] == "deviation"]
    comparable = sum(sample["status"] in {"deviation", "within_threshold"} for sample in pose_samples)
    if confirmed:
        anomalies.append(
            VideoAnomaly(
                code="trunk_inclination",
                severity="high",
                title="Inclinação do tronco acima do limite demonstrativo",
                description="OpenPose e YOLOv8 Pose confirmaram a inclinação nas amostras indicadas.",
                observed_value=max(min(item["openpose_degrees"], item["yolov8_degrees"]) for item in confirmed),
                threshold=TRUNK_DEVIATION_DEGREES,
                unit="degrees",
                intervals=[_interval(item["frame"], item["frame"], fps) for item in confirmed],
            )
        )

    return VideoAnalysis(
        decoder="opencv",
        width=width,
        height=height,
        fps=round(fps, 3),
        duration_seconds=round(duration, 3),
        source_frame_count=source_frame_count,
        analyzed_frame_count=analyzed_frames,
        sample_every_n_frames=sample_every_n_frames,
        mean_motion_percent=round(mean_motion, 4),
        peak_motion_percent=round(peak_motion, 4),
        activity_label=_activity_label(mean_motion, low_motion_threshold, abrupt_motion_threshold),
        anomalies=[asdict(item) for item in anomalies],
        coverage={
            "sampled_interval": _interval(0, last_sample, fps),
            "decoded_frames": frame_index,
            "sample_limit_reached": analyzed_frames == max_frames,
        },
        pose_analysis={
            "models": list(POSE_MODELS),
            "status": (
                "unavailable" if pose_analyzer is None else "evaluated" if comparable else "insufficient_evidence"
            ),
            "reason": pose_reason if pose_analyzer is None else None,
            "threshold_degrees": TRUNK_DEVIATION_DEGREES,
            "comparable_frames": comparable,
            "samples": pose_samples,
        },
    )


def create_synthetic_low_motion_video(
    destination: Path,
    *,
    seconds: float = 2.0,
    fps: int = 10,
    width: int = 320,
    height: int = 240,
) -> Path:
    """Create a deterministic geometric video containing no person or medical data."""
    _require_opencv()
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(destination),
        cv2.VideoWriter_fourcc(*"MJPG"),
        float(fps),
        (width, height),
    )
    if not writer.isOpened():
        raise VideoProcessingError("Synthetic demo video could not be created")
    try:
        total_frames = max(2, int(seconds * fps))
        for frame_index in range(total_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            x = 40 + frame_index // max(1, fps)
            cv2.rectangle(frame, (x, 80), (x + 60, 160), (80, 180, 255), -1)
            cv2.putText(frame, "SYNTHETIC", (100, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            writer.write(frame)
    finally:
        writer.release()
    return destination


def create_synthetic_posture_video(destination: Path, image_path: Path) -> Path:
    """Create a short video from the project's fictional posture image."""
    _require_opencv()
    try:
        image = image_path.read_bytes()
    except OSError as exc:
        raise VideoProcessingError("A imagem sintética de postura não está disponível.") from exc
    frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR) if image else None
    if frame is None:
        raise VideoProcessingError("A imagem sintética de postura não está disponível.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    height, width = frame.shape[:2]
    cv2.putText(frame, "SYNTHETIC", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (25, 25, 25), 2)
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (width, height))
    try:
        if not writer.isOpened():
            raise VideoProcessingError("Synthetic demo video could not be created")
        for _ in range(18):
            writer.write(frame)
    finally:
        writer.release()
    return destination

