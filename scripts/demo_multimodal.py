"""Reproducible, educational MedGuard AI three-source demo.

Run inside the API container so OpenCV, Azure config and the audio fixture
are available. Uses existing public REST endpoints; no direct DB mutation.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from pathlib import Path

import requests

from app.modules.video.processor import create_synthetic_low_motion_video


class DemoError(RuntimeError):
    pass


def call(session: requests.Session, method: str, url: str, *, expected: int, **kwargs):
    try:
        response = session.request(method, url, timeout=90, **kwargs)
    except requests.RequestException as exc:
        raise DemoError(f"{method} {url}: connection failed: {exc}") from exc
    if response.status_code != expected:
        raise DemoError(
            f"{method} {url}: expected HTTP {expected}, received {response.status_code}: "
            f"{response.text[:1500]}"
        )
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audio", type=Path, required=True,
        help="Existing WAV file containing entirely fictional, synthetic spoken words in pt-BR",
    )
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--window", type=int, default=5, help="Correlation window in minutes (1-60)")
    parser.add_argument("--patient-code", default=None)
    args = parser.parse_args()

    if not args.audio.is_file():
        parser.error(f"Audio fixture not found: {args.audio}")
    if not 1 <= args.window <= 60:
        parser.error("--window must be between 1 and 60")
    if args.audio.suffix.lower() != ".wav":
        parser.error("--audio must be a WAV file")

    base = args.api_url.rstrip("/")
    code = args.patient_code or f"MG-MULTI-{uuid.uuid4().hex[:8].upper()}"
    session = requests.Session()

    print(f"1. Creating synthetic patient {code} ...", flush=True)
    patient = call(session, "POST", f"{base}/patients", expected=201, json={
        "code": code,
        "alias": "Paciente Multimodal Ficticio",
        "birth_year": 1990,
        "notes": "Cenario educacional 100% sintetico para demonstracao FIAP.",
        "is_synthetic": True,
    })
    patient_id = patient["id"]
    print(f"   patient_id={patient_id}", flush=True)

    print("2. Generating and processing a geometric synthetic video ...", flush=True)
    with tempfile.TemporaryDirectory() as folder:
        video_path = Path(folder) / "demo_geometrico_sintetico.avi"
        create_synthetic_low_motion_video(video_path)
        with video_path.open("rb") as fp:
            video_upload = call(session, "POST", f"{base}/patients/{patient_id}/media", expected=201,
                files={"file": (video_path.name, fp, "video/x-msvideo")},
                data={"kind": "video", "is_synthetic": "true"})
        video_processed = call(session, "POST", f"{base}/jobs/{video_upload['job']['id']}/process", expected=200)
    video_events = video_processed.get("events", [])
    print(f"   video events={len(video_events)}", flush=True)
    if not video_events:
        raise DemoError("No synthetic video event produced. Check video thresholds before continuing.")

    print("3. Uploading and processing the fictional spoken WAV with Azure Speech ...", flush=True)
    with args.audio.open("rb") as fp:
        audio_upload = call(session, "POST", f"{base}/patients/{patient_id}/media", expected=201,
            files={"file": (args.audio.name, fp, "audio/wav")},
            data={"kind": "audio", "is_synthetic": "true"})
    audio_processed = call(session, "POST", f"{base}/jobs/{audio_upload['job']['id']}/process", expected=200)
    audio_events = audio_processed.get("events", [])
    print(f"   audio review events={len(audio_events)}", flush=True)
    if not audio_events:
        raise DemoError(
            "Audio job completed but created no review event. Ensure the WAV contains a clearly affirmative, "
            "fictional pt-BR phrase such as 'Preciso de ajuda, estou sentindo dor' and Azure Speech is configured."
        )

    print("4. Recording an intentionally anomalous synthetic vital measurement ...", flush=True)
    measurement = call(session, "POST", f"{base}/patients/{patient_id}/measurements", expected=201,
        json={"heart_rate_bpm": 145, "spo2_percent": 90,
              "systolic_mmhg": 125, "diastolic_mmhg": 80,
              "source": "fiap_multimodal_demo", "is_synthetic": True})
    vital_events = [event for event in measurement.get("events", []) if event.get("source") == "vital_signs"]
    print(f"   vital anomaly events={len(vital_events)}", flush=True)
    if not vital_events:
        raise DemoError("The measurement generated no vital_signs anomaly event.")

    print("5. Correlating three modalities ...", flush=True)
    endpoint = f"{base}/patients/{patient_id}/correlations/run-v2"
    created = call(session, "POST", endpoint, expected=200, params={"window_minutes": args.window})
    triples = [e for e in created if set(e.get("payload", {}).get("sources", [])) == {"audio", "video", "vital"}]
    print(f"   new correlations={len(created)}, three-source correlations={len(triples)}", flush=True)

    print("6. Re-running correlation to verify idempotency ...", flush=True)
    repeated = call(session, "POST", endpoint, expected=200, params={"window_minutes": args.window})
    print(f"   additional correlations on repeat={len(repeated)}", flush=True)

    print("7. Reading back persisted patient events and alerts ...", flush=True)
    events = call(session, "GET", f"{base}/events", expected=200, params={"patient_id": patient_id, "limit": 500})
    alerts = call(session, "GET", f"{base}/alerts", expected=200, params={"patient_id": patient_id, "limit": 500})
    summary = {
        "patient_id": patient_id,
        "patient_code": code,
        "video_events": len(video_events),
        "audio_events": len(audio_events),
        "vital_anomaly_events": len(vital_events),
        "created_correlations": len(created),
        "three_source_correlations": len(triples),
        "repeat_created_correlations": len(repeated),
        "persisted_events": len(events),
        "persisted_alerts": len(alerts),
        "correlation_ids": [e["id"] for e in triples],
        "result": "PASS" if triples and not repeated else "REVIEW",
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    if not triples:
        raise DemoError(
            "No three-source correlation was created. Check that processing finished within "
            f"the {args.window}-minute window, and that all source events belong to the same patient."
        )
    if repeated:
        raise DemoError("Repeated execution created duplicate correlations")
    print("Demo succeeded. Choose this patient in Streamlit's multimodal dashboard.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DemoError as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
