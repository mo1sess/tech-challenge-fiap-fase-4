from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from app.modules.audio.azure_healthcare import CLINICAL_MENTIONS_DISCLAIMER
from app.modules.audio.azure_language import SENTIMENT_DISCLAIMER

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("succeeded", None),
        ("skipped", "speech_not_recognized"),
        ("unavailable", "missing_configuration"),
        (None, None),
    ],
)
def test_dashboard_processes_audio_and_displays_persisted_result(monkeypatch, status, reason):
    selected_job = {
        "id": "selected-audio",
        "job_type": "audio_analysis",
        "status": "queued" if status else "completed",
        "result": {},
    }
    text = "Adorei o passeio. A comida foi péssima."
    scores = {"positive": 0.46, "neutral": 0.02, "negative": 0.52}
    analysis = {"transcription": {"text": "" if status == "skipped" else text}}
    if status:
        sentiment = {
            "provider": "azure_ai_language",
            "language": "pt-BR",
            "status": status,
            "disclaimer": SENTIMENT_DISCLAIMER,
        }
        if reason:
            sentiment["reason"] = reason
        else:
            sentiment.update(
                sentiment="mixed",
                confidence_scores=scores,
                sentences=[
                    {
                        "text": "Adorei o passeio.",
                        "sentiment": "positive",
                        "confidence_scores": {"positive": 0.98, "neutral": 0.01, "negative": 0.01},
                    },
                ],
            )
        analysis["sentiment_analysis"] = sentiment
        analysis["clinical_mentions"] = {
            "disclaimer": CLINICAL_MENTIONS_DISCLAIMER,
            "status": status,
            "language": "pt",
            "reason": reason,
            "mentions": [
                {
                    "text": "falta de ar",
                    "category": "SymptomOrSign",
                    "context": {"certainty": "negative", "association": None, "conditionality": None},
                    "confidence_score": 0.95,
                },
            ],
        }

    if not status:
        selected_job["result"] = {"analysis": analysis}
    jobs = [
        {"id": "other-audio", "job_type": "audio_analysis", "status": "queued", "result": {}},
        {"id": "video", "job_type": "video_analysis", "status": "queued", "result": {}},
        selected_job,
    ]
    processed_jobs = []

    def request(method, url, **kwargs):
        path = url.split("/api/v1", 1)[1]
        payload = []
        if method == "GET" and path == "/jobs?limit=20":
            payload = jobs
        elif method == "POST":
            assert path == "/jobs/selected-audio/process"
            processed_jobs.append(path)
            selected_job.update(status="completed", result={"analysis": analysis})
            payload = {"job": selected_job, "events": [], "alerts": []}
        return Mock(**{"json.return_value": payload})

    monkeypatch.setattr("requests.request", request)
    app = AppTest.from_file(str(DASHBOARD), default_timeout=10).run()
    selector = app.selectbox(key="audio_job_id")
    assert len(selector.options) == 2
    selector.select("selected-audio").run()
    button = next(button for button in app.button if button.label == "Processar áudio selecionado")
    if status:
        button.click().run()
        assert processed_jobs == ["/jobs/selected-audio/process"]
    else:
        assert button.disabled

    assert not app.exception
    assert app.text[0].value == ("Sem texto reconhecido." if status == "skipped" else text)
    azure_source = "Resultado do Azure AI Language · pt-BR"
    assert any(caption.value == azure_source for caption in app.caption) == (status == "succeeded")
    if status == "succeeded":
        assert [metric.value for metric in app.metric] == ["Misto", "0.46", "0.02", "0.52"]
        sentences = next(frame.value for frame in app.dataframe if "Sentença" in frame.value.columns)
        assert sentences.iloc[0]["Sentença"] == "Adorei o passeio."
        mentions = next(frame.value for frame in app.dataframe if "Confiança da extração" in frame.value.columns)
        assert mentions.iloc[0]["Trecho"] == "falta de ar"
        assert mentions.iloc[0]["Certeza"] == "negative"
    elif status == "unavailable":
        assert any("(unavailable)" in warning.value for warning in app.warning)
        assert any("Extração indisponível" in warning.value for warning in app.warning)
    elif status == "skipped":
        assert any("(skipped)" in info.value for info in app.info)
        assert any("Extração não executada" in info.value for info in app.info)
    else:
        assert any("sem um resultado de sentimento" in info.value for info in app.info)
