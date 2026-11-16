import sys
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.modules.video.pose import analyze_pose
from app.modules.video.processor import analyze_video, create_synthetic_low_motion_video, VideoProcessingError


def test_disabled_and_model_missing(tmp_path):
    assert analyze_pose(tmp_path / "x", Settings(_env_file=None, video_pose_enabled=False))["status"] == "disabled"
    result = analyze_pose(tmp_path / "x", Settings(_env_file=None, video_pose_enabled=True, video_pose_model_path=None))
    assert result["status"] == "model_unavailable"
    assert result["anomalies"] == []


@pytest.mark.parametrize("with_person", [False, True])
def test_mock_pose_metrics(tmp_path, monkeypatch, with_person):
    path = create_synthetic_low_motion_video(tmp_path / "geometric.avi")
    model = tmp_path / "model.task"
    model.write_bytes(b"mock-only")
    monkeypatch.setitem(sys.modules, "mediapipe", NS(Image=lambda **kw: kw, ImageFormat=NS(SRGB=1)))
    detector = MagicMock()
    detector.__enter__.return_value = detector
    counter = iter(range(100))
    def detect(image):
        x = next(counter) % 2 * .5
        return NS(pose_landmarks=[[NS(x=x, y=.5, visibility=.99) for _ in range(33)]] if with_person else [])
    detector.detect.side_effect = detect
    monkeypatch.setattr("app.modules.video.pose.create_detector", lambda path: detector)
    result = analyze_pose(path, Settings(_env_file=None, video_pose_enabled=True, video_pose_model_path=str(model)))
    assert result["status"] == ("completed" if with_person else "no_pose")
    if with_person:
        assert result["peak_displacement"] == .5
        assert result["anomalies"][0]["code"] == "pose_displacement_review"
        assert len(result["landmarks"]) == 33
    else:
        assert result["anomalies"] == []
        assert result["peak_displacement"] is None
    # A geometria continua sendo avaliada independentemente de pose.
    assert analyze_video(path).anomalies


def test_pose_missing_dependency(tmp_path, monkeypatch):
    model = tmp_path / "local.task"
    model.write_bytes(b"mock")
    monkeypatch.setitem(sys.modules, "mediapipe", None)
    result = analyze_pose(tmp_path / "x", Settings(_env_file=None, video_pose_enabled=True, video_pose_model_path=str(model)))
    assert result["status"] == "dependency_unavailable"


def test_invalid_video(tmp_path):
    path = tmp_path / "invalid.avi"
    path.write_bytes(b"not a video")
    with pytest.raises(VideoProcessingError):
        analyze_video(path)


def test_nonconsecutive_poses_do_not_claim_zero_movement(tmp_path, monkeypatch):
    path = create_synthetic_low_motion_video(tmp_path / "gaps.avi")
    model = tmp_path / "model.task"
    model.write_bytes(b"mock-only")
    monkeypatch.setitem(sys.modules, "mediapipe", NS(Image=lambda **kw: kw, ImageFormat=NS(SRGB=1)))
    detector = MagicMock()
    detector.__enter__.return_value = detector
    outputs = iter(range(100))
    detector.detect.side_effect = lambda image: NS(pose_landmarks=(
        [[NS(x=.5, y=.5, visibility=.99) for _ in range(33)]]
        if next(outputs) % 2 == 0 else []))
    monkeypatch.setattr("app.modules.video.pose.create_detector", lambda path: detector)
    result = analyze_pose(path, Settings(_env_file=None, video_pose_enabled=True, video_pose_model_path=str(model)))
    assert result["detected_frames"] > 1
    assert result["compared_pairs"] == 0
    assert result["peak_displacement"] is None
    assert result["anomalies"] == []
