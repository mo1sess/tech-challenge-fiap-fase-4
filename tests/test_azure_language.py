import json
from unittest.mock import MagicMock

import pytest
import requests
from azure.ai.textanalytics import (
    AnalyzeSentimentResult,
    DocumentError,
    SentenceSentiment,
    SentimentConfidenceScores,
    TextAnalyticsError,
)
from azure.core.exceptions import HttpResponseError
from azure.core.pipeline.transport import RequestsTransportResponse

from app.core.config import Settings
from app.modules.audio.azure_language import MAX_TEXT_ELEMENTS, analyze_sentiment


@pytest.fixture
def language_settings() -> Settings:
    return Settings(
        _env_file=None,
        azure_language_endpoint="https://language.example.invalid",
        azure_language_key="dummy-key",
    )


@pytest.fixture
def client_class(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mocked_class = MagicMock()
    monkeypatch.setattr("app.modules.audio.azure_language.TextAnalyticsClient", mocked_class)
    return mocked_class


@pytest.mark.parametrize(
    ("label", "scores", "sentence_labels"),
    [
        ("positive", (0.95, 0.04, 0.01), ["positive"]),
        ("neutral", (0.02, 0.97, 0.01), ["neutral"]),
        ("negative", (0.01, 0.04, 0.95), ["negative"]),
        ("mixed", (0.46, 0.02, 0.52), ["positive", "negative"]),
    ],
)
def test_analyzes_complete_portuguese_text_and_serializes_scores(
    client_class, language_settings, label, scores, sentence_labels
):
    confidence_scores = dict(zip(("positive", "neutral", "negative"), scores))
    sentence_scores = dict(positive=0.2, neutral=0.5, negative=0.3)
    phrases = ["Frase fictícia um.", "Frase fictícia dois."][:len(sentence_labels)]
    text = " ".join(phrases)
    client = client_class.return_value.__enter__.return_value
    client.analyze_sentiment.return_value = [
        AnalyzeSentimentResult(
            id="0",
            sentiment=label,
            confidence_scores=SentimentConfidenceScores(**confidence_scores),
            sentences=[
                SentenceSentiment(
                    text=phrase,
                    sentiment=sentence_label,
                    confidence_scores=SentimentConfidenceScores(**sentence_scores),
                )
                for phrase, sentence_label in zip(phrases, sentence_labels)
            ],
            warnings=[],
        )
    ]

    result = json.loads(json.dumps(analyze_sentiment(text, language_settings)))

    assert result["provider"] == "azure_ai_language"
    assert result["language"] == "pt-BR"
    assert result["status"] == "succeeded"
    assert result["sentiment"] == label
    assert result["confidence_scores"] == confidence_scores
    assert result["sentences"] == [
        {"text": phrase, "sentiment": sentence_label, "confidence_scores": sentence_scores}
        for phrase, sentence_label in zip(phrases, sentence_labels)
    ]
    assert client_class.call_args.kwargs["endpoint"] == language_settings.azure_language_endpoint
    assert client_class.call_args.kwargs["credential"].key == language_settings.azure_language_key
    client.analyze_sentiment.assert_called_once_with(
        [text], language="pt-BR", disable_service_logs=True
    )
    client_class.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("missing_setting", ["azure_language_endpoint", "azure_language_key"])
def test_requires_both_azure_settings(client_class, language_settings, missing_setting):
    setattr(language_settings, missing_setting, " ")
    result = analyze_sentiment("Um texto fictício.", language_settings)
    assert result["status"] == "unavailable"
    assert result["reason"] == "missing_configuration"
    client_class.assert_not_called()


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (HttpResponseError("raw dummy-key"), "service_error"),
        (TypeError("raw dummy-key"), "invalid_response"),
        ([DocumentError(id="0", error=TextAnalyticsError(message="raw dummy-key"))], "document_error"),
        ([], "invalid_response"),
    ],
)
def test_azure_failures_return_only_safe_information(client_class, language_settings, failure, reason):
    client = client_class.return_value.__enter__.return_value
    if isinstance(failure, Exception):
        client.analyze_sentiment.side_effect = failure
    else:
        client.analyze_sentiment.return_value = failure

    result = analyze_sentiment("Um texto fictício.", language_settings)
    assert result["status"] == "unavailable"
    assert result["reason"] == reason
    assert "raw dummy-key" not in json.dumps(result)
    assert "confidence_scores" not in result


def test_counts_unicode_text_elements_at_limit(client_class, language_settings):
    text = "a\u0301" * MAX_TEXT_ELEMENTS
    client = client_class.return_value.__enter__.return_value
    client.analyze_sentiment.return_value = []

    analyze_sentiment(text, language_settings)

    client.analyze_sentiment.assert_called_once_with(
        [text], language="pt-BR", disable_service_logs=True
    )


@pytest.mark.parametrize(
    "text",
    ["a" * (MAX_TEXT_ELEMENTS + 1), "a" + "\u0301" * 200_000],
    ids=["text-elements", "encoded-size"],
)
def test_rejects_oversized_documents_without_truncating(client_class, language_settings, text):
    result = analyze_sentiment(text, language_settings)
    assert result["status"] == "unavailable"
    assert result["reason"] == "document_too_large"
    client_class.assert_not_called()


def test_sdk_sends_portuguese_and_deserializes_a_response_without_network(monkeypatch, language_settings):
    text = "Adorei o passeio."

    def send(_transport, request, **kwargs):
        payload = json.loads(request.body)
        assert payload["kind"] == "SentimentAnalysis"
        assert payload["parameters"]["loggingOptOut"] is True
        document, = payload["analysisInput"]["documents"]
        assert document["language"] == "pt-BR"
        assert document["text"] == text
        scores = {"positive": 0.98, "neutral": 0.01, "negative": 0.01}
        body = {
            "kind": "SentimentAnalysisResults",
            "results": {
                "documents": [
                    {
                        "id": document["id"],
                        "sentiment": "positive",
                        "confidenceScores": scores,
                        "sentences": [
                            {
                                "text": text,
                                "sentiment": "positive",
                                "confidenceScores": scores,
                                "offset": 0,
                                "length": len(text),
                            },
                        ],
                        "warnings": [],
                    },
                ],
                "errors": [],
                "modelVersion": "example",
            },
        }
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(body).encode("utf-8")
        return RequestsTransportResponse(request, response)

    monkeypatch.setattr("azure.core.pipeline.transport.RequestsTransport.send", send)
    result = analyze_sentiment(text, language_settings)

    assert result["status"] == "succeeded"
    assert result["sentiment"] == "positive"
    assert result["sentences"][0]["text"] == text
