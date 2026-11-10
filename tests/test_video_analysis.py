import importlib.util
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.modules.video.processor import (VideoAnalysis,
                                         create_synthetic_low_motion_video)

pytestmark = pytest.mark.anyio


async def test_video_upload_processes_and_creates_alert(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.video_flow.analyze_video", lambda *args, **kwargs: fake_low_motion_analysis())
    response = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("synthetic.avi", b"synthetic-video-test", "video/x-msvideo")},
        data={"is_synthetic": "true"},
    )
    assert response.status_code == 201
    uploaded = response.json()
    assert uploaded["media"]["kind"] == "video"
    assert uploaded["job"]["status"] == "queued"
    assert uploaded["job"]["result"]["pipeline"]["status"] == "ready"

    processed = await client.post(f"/api/v1/jobs/{uploaded['job']['id']}/process")
    assert processed.status_code == 200
    body = processed.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["progress"] == 100.0
    assert body["job"]["result"]["analysis"]["decoder"] == "opencv"
    assert body["job"]["result"]["analysis"]["activity_label"] == "very_low_motion"
    assert body["events"][0]["source"] == "video_analysis"
    assert body["alerts"][0]["status"] == "open"

    events = await client.get(f"/api/v1/events?patient_id={patient['id']}")
    alerts = await client.get(f"/api/v1/alerts?patient_id={patient['id']}")
    assert any(item["event_type"] == "sustained_low_motion" for item in events.json())
    assert len(alerts.json()) == 1


async def test_video_demo_is_end_to_end(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_video(destination: Path) -> Path:
        destination.write_bytes(b"synthetic-video-demo")
        return destination

    monkeypatch.setattr("app.api.routes.demo.create_synthetic_low_motion_video", fake_video)
    monkeypatch.setattr("app.services.video_flow.analyze_video", lambda *args, **kwargs: fake_low_motion_analysis())
    response = await client.post("/api/v1/demo/video-alert")
    assert response.status_code == 200
    body = response.json()
    assert body["patient"]["is_synthetic"] is True
    assert body["media"]["kind"] == "video"
    assert body["processing"]["job"]["status"] == "completed"
    assert body["processing"]["alerts"]





async def test_completed_video_job_is_not_processed_twice(
    client: AsyncClient,
    patient: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.video_flow.analyze_video", lambda *args, **kwargs: fake_low_motion_analysis())
    uploaded = await client.post(
        f"/api/v1/patients/{patient['id']}/media",
        files={"file": ("once.avi", b"synthetic-video-once", "video/x-msvideo")},
        data={"is_synthetic": "true"},
    )
    job_id = uploaded.json()["job"]["id"]
    first = await client.post(f"/api/v1/jobs/{job_id}/process")
    second = await client.post(f"/api/v1/jobs/{job_id}/process")
    assert first.status_code == 200
    assert second.status_code == 409


def fake_low_motion_analysis() -> VideoAnalysis:
    return VideoAnalysis(
        decoder="opencv",
        width=320,
        height=240,
        fps=10.0,
        duration_seconds=2.0,
        source_frame_count=20,
        analyzed_frame_count=7,
        sample_every_n_frames=3,
        mean_motion_percent=0.02,
        peak_motion_percent=0.1,
        activity_label="very_low_motion",
        anomalies=[
            {
                "code": "sustained_low_motion",
                "severity": "high",
                "title": "Baixa variacao de movimento no video sintetico",
                "description": "Resultado controlado para o teste automatizado.",
                "observed_value": 0.02,
                "threshold": 0.35,
                "unit": "percent_changed_pixels",
            }
        ],
    )


@pytest.mark.skipif(importlib.util.find_spec("cv2") is None, reason="OpenCV is installed by the project dependencies")
def test_real_opencv_processor_reads_synthetic_video(tmp_path: Path) -> None:
    video_path = create_synthetic_low_motion_video(tmp_path / "real.avi")
    from app.modules.video.processor import analyze_video

    result = analyze_video(video_path)
    assert result.decoder == "opencv"
    assert result.analyzed_frame_count >= 2
    assert result.anomalies
