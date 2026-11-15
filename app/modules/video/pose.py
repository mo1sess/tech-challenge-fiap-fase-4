from dataclasses import dataclass
from math import atan2, degrees
from pathlib import Path

import cv2
import numpy as np

POSE_MODELS = ("OpenPose COCO", "YOLOv8n Pose")
POSE_SAMPLE_LIMIT = 12
TRUNK_DEVIATION_DEGREES = 30.0
MAX_MODEL_DIFFERENCE_DEGREES = 20.0
YOLO_INPUT_SIZE = 640
OPENPOSE_INPUT_SIZE = 256
YOLO_TORSO = [5, 6, 11, 12]
OPENPOSE_TORSO = [5, 2, 11, 8]


@dataclass(frozen=True)
class Letterbox:
    image: np.ndarray
    left: int
    top: int
    scale_x: float
    scale_y: float

    def original_points(self, points: np.ndarray) -> np.ndarray:
        return (points - (self.left, self.top)) / (self.scale_x, self.scale_y)


def _letterbox(frame: np.ndarray, size: int, padding: int) -> Letterbox:
    height, width = frame.shape[:2]
    scale = size / max(height, width)
    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    left, top = (size - resized_width) // 2, (size - resized_height) // 2
    resized = cv2.resize(frame, (resized_width, resized_height))
    image = np.full((size, size, 3), padding, dtype=np.uint8)
    image[top:top + resized_height, left:left + resized_width] = resized
    return Letterbox(image, left, top, resized_width / width, resized_height / height)


def _trunk_angle(points: np.ndarray) -> float | None:
    if not np.isfinite(points).all():
        return None
    dx, dy = points[2:].mean(axis=0) - points[:2].mean(axis=0)
    if abs(dx) + abs(dy) < 1e-6:
        return None
    return degrees(atan2(abs(dx), dy))


class PoseAnalyzer:
    """Estimate the torso angle in frames with a single detected person."""

    def __init__(self, directory: Path) -> None:
        definition = directory / "pose_deploy_linevec.prototxt"
        weights = directory / "pose_iter_440000.caffemodel"
        yolo = directory / "yolov8n-pose.onnx"
        if not all(path.is_file() for path in (definition, weights, yolo)):
            raise FileNotFoundError("Arquivos de OpenPose e YOLOv8 Pose incompletos.")
        self._yolo = cv2.dnn.readNetFromONNX(str(yolo))
        self._openpose = cv2.dnn.readNetFromCaffe(str(definition), str(weights))

    def _yolo_detections(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        prepared = _letterbox(frame, YOLO_INPUT_SIZE, 114)
        self._yolo.setInput(cv2.dnn.blobFromImage(prepared.image, 1 / 255, swapRB=True))
        output = self._yolo.forward()
        if output.ndim != 3 or output.shape[:2] != (1, 56):
            raise ValueError("Esperada a saída ONNX de YOLOv8 Pose sem NMS embutido.")
        predictions = output[0].T
        usable = (
            np.isfinite(predictions[:, :5]).all(axis=1)
            & (predictions[:, 4] >= 0.4)
            & (predictions[:, 2:4] > 0).all(axis=1)
        )
        candidates = predictions[usable]
        if not len(candidates):
            return candidates, prepared.original_points(np.empty((0, 2, 2)))

        boxes = candidates[:, :4].copy()
        boxes[:, :2] -= boxes[:, 2:4] / 2
        keep = np.asarray(
            cv2.dnn.NMSBoxes(boxes.tolist(), candidates[:, 4].tolist(), 0.4, 0.45),
            dtype=int,
        ).reshape(-1)
        selected = candidates[keep].copy()
        boxes = boxes[keep]
        bounds = np.stack([boxes[:, :2], boxes[:, :2] + boxes[:, 2:4]], axis=1)
        points = selected[:, 5:].reshape(-1, 17, 3)
        points[..., :2] = prepared.original_points(points[..., :2])
        return selected, prepared.original_points(bounds)

    def _openpose_angle(self, crop: np.ndarray) -> float | None:
        prepared = _letterbox(crop, OPENPOSE_INPUT_SIZE, 128)
        self._openpose.setInput(
            cv2.dnn.blobFromImage(prepared.image, 1 / 256, mean=(128, 128, 128))
        )
        output = self._openpose.forward()
        if output.ndim != 4 or output.shape[:2] != (1, 57):
            raise ValueError("Esperados 57 canais no modelo OpenPose COCO.")
        heatmap_height, heatmap_width = output.shape[2:]
        points = []
        for index in OPENPOSE_TORSO:
            _, confidence, _, (x, y) = cv2.minMaxLoc(output[0, index])
            if confidence < 0.15:
                return None
            points.append((
                (x + 0.5) * OPENPOSE_INPUT_SIZE / heatmap_width,
                (y + 0.5) * OPENPOSE_INPUT_SIZE / heatmap_height,
            ))
        original = prepared.original_points(np.asarray(points))
        height, width = crop.shape[:2]
        if not ((original >= 0) & (original < (width, height))).all():
            return None
        return _trunk_angle(original)

    def evaluate(self, frame: np.ndarray) -> dict[str, str | float | None]:
        candidates, boxes = self._yolo_detections(frame)
        if len(candidates) != 1:
            return {"status": "no_person" if not len(candidates) else "multiple_people"}

        yolo_points = candidates[0, 5:].reshape(17, 3)[YOLO_TORSO]
        height, width = frame.shape[:2]
        coordinates = yolo_points[:, :2]
        if not (
            (yolo_points[:, 2] >= 0.35).all()
            and ((coordinates >= 0) & (coordinates < (width, height))).all()
        ):
            return {"status": "low_confidence"}

        bounds = boxes[0]
        margin = (bounds[1] - bounds[0]) * 0.15
        left, top = np.maximum(np.floor(bounds[0] - margin), (0, 0)).astype(int)
        right, bottom = np.minimum(np.ceil(bounds[1] + margin), (width, height)).astype(int)
        if right <= left or bottom <= top:
            return {"status": "low_confidence"}

        yolo_angle = _trunk_angle(coordinates)
        openpose_angle = self._openpose_angle(frame[top:bottom, left:right])
        measurements = {
            "yolov8_degrees": round(yolo_angle, 1) if yolo_angle is not None else None,
            "openpose_degrees": round(openpose_angle, 1) if openpose_angle is not None else None,
        }
        if yolo_angle is None or openpose_angle is None:
            return {"status": "low_confidence", **measurements}
        if abs(yolo_angle - openpose_angle) > MAX_MODEL_DIFFERENCE_DEGREES:
            return {"status": "disagreement", **measurements}
        lower = min(yolo_angle, openpose_angle)
        higher = max(yolo_angle, openpose_angle)
        if lower < TRUNK_DEVIATION_DEGREES <= higher:
            return {"status": "disagreement", **measurements}
        status = "deviation" if lower >= TRUNK_DEVIATION_DEGREES else "within_threshold"
        return {"status": status, **measurements}
