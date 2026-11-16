import pytest
from test_video_analysis import fake_low_motion_analysis


@pytest.mark.anyio
async def test_pose_event_and_existing_video_contract(client, patient, monkeypatch):
    monkeypatch.setattr("app.services.video_flow.analyze_video", lambda *a, **k: fake_low_motion_analysis())
    monkeypatch.setattr("app.services.video_flow.analyze_pose", lambda *a: {
        "status": "completed", "anomalies": [{"code": "pose_displacement_review", "severity": "medium",
        "title": "Pose sintética", "description": "Revisão demonstrativa", "observed_value": .5, "threshold": .15, "unit": "normalized_image_distance"}]})
    uploaded = await client.post(f"/api/v1/patients/{patient['id']}/media", files={"file": ("avatar.avi", b"mock", "video/x-msvideo")})
    job_id = uploaded.json()['job']['id']
    result = (await client.post(f"/api/v1/jobs/{job_id}/process")).json()
    assert len(result['events']) == 2
    assert len(result['alerts']) == 2
    assert all(e['payload']['job_id'] == job_id for e in result['events'])
    assert result['job']['result']['analysis']['pose']['status'] == 'completed'
    assert all(e['payload']['requires_human_review'] for e in result['events'])
