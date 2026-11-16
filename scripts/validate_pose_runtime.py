"""Valida o modelo real e cria novos registros sintéticos pela API.

Execute após preparar os vídeos de movimento suave e abrupto. Esta validação
é independente dos testes Pytest com simulações. As evidências permanecem
em storage/validation, ignorado pelo Git, sem exibir credenciais."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from time import perf_counter
import uuid

import cv2
import mediapipe as mp
import numpy as np
import requests

from app.core.config import Settings
from app.modules.video.pose import analyze_pose, create_detector
from app.modules.video.processor import analyze_video, create_synthetic_low_motion_video


def inspect_landmarks(path, model, output):
    """Registra inferência real, articulação dos braços e sobreposição dos pontos."""
    capture = cv2.VideoCapture(str(path))
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"MJPG"), 4, (960, 864))
    if not writer.isOpened():
        raise RuntimeError("Overlay encoder unavailable")
    frames = []
    started = perf_counter()
    try:
        with create_detector(model) as detector:
            index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index % 3 == 0:
                    result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                    landmarks = result.pose_landmarks[0] if result.pose_landmarks else []
                    points = [{"x": p.x, "y": p.y, "z": p.z,
                               "visibility": p.visibility, "presence": p.presence} for p in landmarks]
                    frames.append({"frame": index, "landmarks": points})
                    for p in points:
                        cv2.circle(frame, (int(p['x']*960), int(p['y']*864)), 3, (0, 0, 230), -1)
                    for a, b in [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28)]:
                        if points:
                            pa, pb = points[a], points[b]
                            cv2.line(frame, (int(pa['x']*960),int(pa['y']*864)),
                                     (int(pb['x']*960),int(pb['y']*864)), (0,180,0), 2)
                    writer.write(frame)
                index += 1
    finally:
        capture.release()
        writer.release()
    valid = [f['landmarks'] for f in frames if len(f['landmarks']) == 33]
    # A posição do punho relativa ao ombro remove a translação global do corpo.
    wrist = [[p[15]['x']-p[11]['x'], p[15]['y']-p[11]['y']] for p in valid]
    return {"elapsed_seconds": round(perf_counter()-started, 3), "frames": frames,
            "raw_detected_frames": len(valid),
            "relative_wrist_range_xy": np.ptp(wrist, axis=0).tolist() if wrist else []}


def run(folder, base):
    settings = Settings()
    assert settings.video_pose_enabled, "Pose must be explicitly enabled"
    model = Path(settings.video_pose_model_path or "")
    assert model.is_file(), "Official model bundle missing"
    report = {"inference": "REAL CPU MODEL; no mocks", "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
              "versions": {p: importlib.metadata.version(p) for p in ['mediapipe','numpy','opencv-python-headless']},
              "sample_every_n_frames": settings.video_sample_every_n_frames,
              "threshold": settings.video_pose_displacement_threshold, "clips": {}}
    session = requests.Session()
    def call(method, endpoint, expected=200, **kwargs):
        response = session.request(method, base.rstrip('/') + endpoint, timeout=180, **kwargs)
        assert response.status_code == expected, f"{endpoint}: HTTP {response.status_code}"
        return response.json()
    patient = call('POST', '/patients', 201, json={"code": 'MG-POSE-'+uuid.uuid4().hex[:8].upper(),
        "alias": "Avatar integralmente sintetico", "is_synthetic": True, "birth_year": 1990})
    report['patient_id'] = patient['id']
    report['patient_code'] = patient['code']
    for name in ['smooth', 'abrupt']:
        path = folder / f'avatar_{name}.avi'
        started = perf_counter()
        pose = analyze_pose(path, settings)
        pose_seconds = round(perf_counter()-started, 3)
        assert pose['status'] == 'completed', f"{name}: {pose['status']}"
        assert len(pose['landmarks']) == 33 and pose['compared_pairs'] > 0
        assert np.isfinite([[p['x'],p['y']] for p in pose['landmarks']]).all()
        visual = analyze_video(path)
        trace = inspect_landmarks(path, str(model), folder / f'avatar_{name}_landmarks.avi')
        (folder / f'{name}_trace.json').write_text(json.dumps(trace, indent=2))
        with path.open('rb') as stream:
            upload = call('POST', f"/patients/{patient['id']}/media", 201,
                files={'file':(path.name,stream,'video/x-msvideo')}, data={'kind':'video','is_synthetic':'true'})
        started = perf_counter()
        processed = call('POST', f"/jobs/{upload['job']['id']}/process")
        pipeline_seconds = round(perf_counter()-started, 3)
        persisted = call('GET', f"/jobs/{upload['job']['id']}")
        assert persisted['status'] == 'completed'
        assert persisted['result'] == processed['job']['result']
        combined = persisted['result']['analysis']
        assert combined['analysis_types'] == ['opencv_frame_difference','mediapipe_pose']
        assert combined['pose'] == pose
        assert combined['mean_motion_percent'] == visual.mean_motion_percent
        assert combined['peak_motion_percent'] == visual.peak_motion_percent
        pose_events = [e for e in processed['events'] if e['event_type']=='pose_displacement_review']
        assert bool(pose_events) == (name == 'abrupt'), f"Unexpected threshold behavior in {name}"
        assert len(processed['alerts']) == len(processed['events'])
        call('POST', f"/jobs/{persisted['id']}/process", 409)
        (folder / f'{name}_job.json').write_text(json.dumps(persisted, indent=2))
        from streamlit.testing.v1 import AppTest
        app_test = AppTest.from_string(
            "import json\nfrom pathlib import Path\n"
            "from dashboard.reports import render_job_report\n"
            f"render_job_report(json.loads(Path({str(folder / f'{name}_job.json')!r}).read_text()))\n"
        ).run(timeout=30)
        assert not app_test.exception, "Persisted pose report failed to render"
        assert any(len(table.value) == 33 for table in app_test.dataframe), "Landmark table missing"
        report['clips'][name] = {'pose':pose, 'opencv':visual.to_dict(), 'pose_seconds':pose_seconds,
            'pipeline_seconds':pipeline_seconds, 'raw_detected_frames':trace['raw_detected_frames'],
            'relative_wrist_range_xy':trace['relative_wrist_range_xy'],
            'report_apptest': 'PASS (33 landmark rows; no exceptions)',
            'job_id':persisted['id'], 'event_ids':[e['id'] for e in processed['events']],
            'alert_ids':[a['id'] for a in processed['alerts']]}
    geometric = create_synthetic_low_motion_video(folder/'geometric_control.avi')
    negative = analyze_pose(geometric, settings)
    assert negative['status'] == 'no_pose' and not negative['anomalies']
    assert analyze_video(geometric).anomalies
    report['negative_control'] = negative
    events = call('GET','/events',params={'patient_id':patient['id'],'limit':500})
    alerts = call('GET','/alerts',params={'patient_id':patient['id'],'limit':500})
    assert {i for c in report['clips'].values() for i in c['event_ids']} == {e['id'] for e in events}
    assert {i for c in report['clips'].values() for i in c['alert_ids']} == {a['id'] for a in alerts}
    report['result'] = 'PASS'
    (folder/'pose_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'result':report['result'], 'patient_id':report['patient_id'],
        'patient_code':report['patient_code'], 'versions':report['versions'],
        'clips':{name:{'status':c['pose']['status'], 'detected_frames':c['pose']['detected_frames'],
            'sampled_frames':c['pose']['sampled_frames'], 'compared_pairs':c['pose']['compared_pairs'],
            'peak_displacement':c['pose']['peak_displacement'], 'pose_seconds':c['pose_seconds'],
            'pipeline_seconds':c['pipeline_seconds'], 'relative_wrist_range_xy':c['relative_wrist_range_xy'],
            'job_id':c['job_id'], 'events':len(c['event_ids']), 'alerts':len(c['alert_ids']),
            'report_apptest':c['report_apptest']} for name,c in report['clips'].items()},
        'negative_control':negative['status']},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=Path('/app/storage/validation'))
    parser.add_argument('--api-url',default='http://localhost:8000/api/v1')
    args = parser.parse_args()
    run(args.folder,args.api_url)
