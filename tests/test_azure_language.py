from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.modules.audio.azure_language import analyze_language


def settings(**kwargs):
    return Settings(_env_file=None, azure_language_endpoint="https://example.cognitiveservices.azure.com", azure_language_key="secret-test", **kwargs)


@pytest.mark.parametrize("label", ["positive", "negative", "neutral", "mixed"])
def test_sentiments_entities_sdk(monkeypatch, label):
    client = MagicMock()
    client.__enter__.return_value = client
    client.analyze_sentiment.return_value = [NS(is_error=False, sentiment=label, confidence_scores=NS(positive=.2, neutral=.3, negative=.5))]
    client.recognize_entities.return_value = [NS(is_error=False, entities=[NS(text="Lisboa", category="Location", subcategory=None, confidence_score=.99, offset=0, length=6)])]
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", constructor)
    result = analyze_language("Lisboa", settings())
    assert result["status"] == "completed"
    assert result["sentiment"]["label"] == label
    assert result["sentiment"]["confidence_scores"]["negative"] == .5
    assert result["entities"][0]["category"] == "Location"
    client.analyze_sentiment.assert_called_once_with(["Lisboa"], language="pt")


def test_empty_and_missing_credentials(monkeypatch):
    constructor = MagicMock()
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", constructor)
    assert analyze_language(" ", settings())["status"] == "empty_text"
    assert analyze_language("texto", Settings(_env_file=None, azure_language_endpoint=None, azure_language_key=None))["status"] == "not_configured"
    constructor.assert_not_called()


@pytest.mark.parametrize("document_error", [True, False])
def test_errors_redacted(monkeypatch, document_error):
    client = MagicMock()
    client.__enter__.return_value = client
    if document_error:
        client.analyze_sentiment.return_value = [NS(is_error=True, error=NS(message="secret-test"))]
    else:
        client.analyze_sentiment.side_effect = RuntimeError("secret-test")
    client.recognize_entities.return_value = [NS(is_error=False, entities=[])]
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", lambda **kw: client)
    result = analyze_language("texto", settings())
    assert result["status"] == "partial"
    assert "secret-test" not in str(result)
    assert result["sentiment"] is None


def test_client_unavailable_and_total_failure(monkeypatch):
    constructor = MagicMock(side_effect=RuntimeError("secret-test"))
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", constructor)
    result = analyze_language("texto", settings())
    assert result["status"] == "error"
    assert "secret-test" not in str(result)
    client = MagicMock()
    client.__enter__.return_value = client
    client.analyze_sentiment.side_effect = RuntimeError("secret-test")
    client.recognize_entities.side_effect = RuntimeError("secret-test")
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", lambda **kw: client)
    assert analyze_language("texto", settings())["status"] == "error"


@pytest.mark.anyio
async def test_result_persisted_with_legacy_events(client, patient, monkeypatch):
    from test_audio_events import process_text
    expected = {"status": "completed", "sentiment": {"label": "mixed"}, "entities": []}
    monkeypatch.setattr("app.services.audio_flow.analyze_language", lambda *args: expected)
    body = await process_text(client, patient, monkeypatch, "Preciso de ajuda.")
    saved = (await client.get(f"/api/v1/jobs/{body['job']['id']}")).json()
    assert saved["result"]["analysis"]["azure_language"] == expected
    assert body["events"][0]["event_type"] == "audio_help_request_review"


@pytest.mark.anyio
async def test_fallback_persisted(client, patient, monkeypatch):
    from test_audio_events import process_text
    body = await process_text(client, patient, monkeypatch, "Preciso de ajuda.")
    assert body["job"]["result"]["analysis"]["azure_language"]["status"] == "not_configured"
    assert len(body["events"]) == 1
