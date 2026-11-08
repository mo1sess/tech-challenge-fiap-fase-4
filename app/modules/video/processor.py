from __future__ import annotations

from dataclasses import asdict, dataclass
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def describe_pipeline(media_path: Path) -> dict[str, object]:
    return {
        "status": "ready",
        "media_path": str(media_path),
        "components": ["opencv_frame_reader", "frame_difference_motion", "event_alert_bridge"],
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
) -> VideoAnalysis:
    """Analyze global frame-to-frame motion without identifying a person."""
    _require_opencv()
    if not media_path.exists():
        raise VideoProcessingError("Video file was not found")

    capture = cv2.VideoCapture(str(media_path))
    if not capture.isOpened():
        raise VideoProcessingError("Video could not be decoded by OpenCV")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    source_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = source_frame_count / fps if fps > 0 else 0.0
    previous: np.ndarray | None = None
    motion_scores: list[float] = []
    analyzed_frames = 0
    frame_index = 0

    try:
        while analyzed_frames < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            current_index = frame_index
            frame_index += 1
            if current_index % sample_every_n_frames != 0:
                continue

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
    peak_motion = float(max(motion_scores))
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

