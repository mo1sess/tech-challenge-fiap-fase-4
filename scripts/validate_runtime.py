"""Validação operacional aditiva, apenas com registros sintéticos novos."""
import json
import uuid
import requests

BASE = "http://localhost:8000/api/v1"


def call(method, path, expected=200, **kwargs):
    response = requests.request(method, BASE + path, timeout=90, **kwargs)
    assert response.status_code == expected, (path, response.status_code, response.text[:300])
    return response.json()


def main():
    patient = call("POST", "/patients", 201, json={"code": "MG-VALID-" + uuid.uuid4().hex[:8], "alias": "Validação fictícia", "is_synthetic": True})
    pid = patient['id']
    assert call("GET", f"/patients/{pid}")['is_synthetic']
    result = call("POST", f"/patients/{pid}/measurements", 201, json={"heart_rate_bpm": 145, "spo2_percent": 90})
    alert = result['alerts'][0]
    path = f"/alerts/{alert['id']}"
    call("PATCH", path, json={"status": "acknowledged", "reviewer": "Revisor fictício operacional"})
    call("PATCH", path, json={"status": "resolved", "note": "Encerramento demonstrativo"})
    history = call("GET", path + "/history", params={"patient_id": pid})
    assert len(history) == 2
    call("POST", f"/patients/{pid}/prescriptions/evaluate", 201, json={"medication_code": "FICTICIO", "action": "started"})
    prescription = call("POST", f"/patients/{pid}/prescriptions/evaluate", 201, json={"medication_code": "FICTICIO", "action": "started"})
    assert prescription['alerts']
    movement = call("POST", f"/patients/{pid}/movements", 201, json={"from_location": "ALA-FICTICIA", "to_location": "ALA-FICTICIA"})
    assert movement['alerts']
    video = call("POST", "/demo/video-alert")
    assert video['processing']['events']
    print(json.dumps({"patient_id": pid, "alert_id": alert['id'], "history_actions": len(history), "video_job": video['processing']['job']['id'], "result": "PASS"}))


if __name__ == '__main__':
    main()
