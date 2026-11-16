"""Pose opcional em CPU com MediaPipe Tasks e pesos fornecidos pelo operador."""
from pathlib import Path

import numpy as np


def create_detector(model_path: str):
    import mediapipe as mp
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_poses=1, min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
    )
    return mp.tasks.vision.PoseLandmarker.create_from_options(options)


def analyze_pose(path: Path, settings) -> dict:
    result = {"analyzer": "mediapipe_pose_landmarker", "status": "disabled",
              "detected_frames": 0, "sampled_frames": 0, "landmarks": [],
              "compared_pairs": 0,
              "peak_displacement": None, "anomalies": [],
              "threshold": settings.video_pose_displacement_threshold,
              "requires_human_review": True,
              "disclaimer": "Deslocamento normalizado em imagem; câmera e perspectiva afetam o resultado. Sem diagnóstico."}
    if not settings.video_pose_enabled:
        return result
    if not settings.video_pose_model_path or not Path(settings.video_pose_model_path).is_file():
        result["status"] = "model_unavailable"
        return result
    capture = None
    try:
        import cv2
        import mediapipe as mp
        previous = None
        peak = 0.0
        with create_detector(settings.video_pose_model_path) as detector:
            capture = cv2.VideoCapture(str(path))
            index = 0
            while result["sampled_frames"] < settings.video_max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                index += 1
                if (index - 1) % settings.video_sample_every_n_frames:
                    continue
                result["sampled_frames"] += 1
                output = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                if not output.pose_landmarks:
                    previous = None
                    continue
                points = output.pose_landmarks[0]
                # Exigir visibilidade de ombros e quadris para a métrica de postura.
                selected = [points[i] for i in (11, 12, 23, 24)]
                if any((p.visibility or 0) < 0.6 for p in selected):
                    previous = None
                    continue
                current = np.array([[p.x, p.y] for p in selected])
                if not np.isfinite(current).all():
                    previous = None
                    continue
                result["detected_frames"] += 1
                result["landmarks"] = [{"index": i, "x": p.x, "y": p.y, "visibility": p.visibility} for i, p in enumerate(points)]
                if previous is not None:
                    result["compared_pairs"] += 1
                    peak = max(peak, float(np.linalg.norm(current - previous, axis=1).mean()))
                previous = current
        result["status"] = "completed" if result["detected_frames"] else "no_pose"
        result["peak_displacement"] = round(peak, 6) if result["compared_pairs"] else None
        if result["peak_displacement"] is not None and peak >= settings.video_pose_displacement_threshold:
            result["anomalies"] = [{"code": "pose_displacement_review", "severity": "medium",
                "title": "Variação demonstrativa de pose", "description": "Deslocamento entre amostras acima do limiar; requer revisão humana.",
                "observed_value": round(peak, 6), "threshold": settings.video_pose_displacement_threshold, "unit": "normalized_image_distance"}]
    except ImportError:
        result["status"] = "dependency_unavailable"
    except Exception:
        result["status"] = "error"
        result["anomalies"] = []
        result["peak_displacement"] = None
    finally:
        if capture is not None:
            capture.release()
    return result
