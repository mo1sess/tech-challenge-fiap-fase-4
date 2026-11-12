import pytest

from app.modules.audio.text_analysis import analyze_text


def test_help_request():
    result = analyze_text("Preciso de ajuda!")
    assert "help_request" in result.matched_signals
    assert result.requires_review


def test_breathing_report():
    result = analyze_text("Estou com dificuldade para respirar.")
    assert "breathing_report" in result.matched_signals


def test_accents():
    result = analyze_text("Tenho DOR DE CABEÇA.")
    assert "pain_report" in result.matched_signals


def test_unrelated_text():
    result = analyze_text("Michael Jordan joga basquete.")
    assert result.matched_signals == []
    assert result.requires_review is False



@pytest.mark.parametrize(
    "sentence,expected_context",
    [
        ("Estou com dor de cabeça.", "affirmed"),
        ("Não estou com dor de cabeça.", "negated"),
        ("Ontem estava com dor de cabeça.", "historical"),
        ("Minha mãe está com dor de cabeça.", "third_party"),
        ("Preciso de ajuda.", "affirmed"),
        ("Não preciso de ajuda.", "negated"),
        ("Não consigo respirar.", "affirmed"),
    ],
)
def test_context_classification(
    sentence: str,
    expected_context: str,
):
    result = analyze_text(sentence)

    assert result.findings
    assert any(
        finding["context"] == expected_context
        for finding in result.findings
    )


def test_negated_symptom_does_not_trigger_review():
    result = analyze_text(
        "Não estou com dor de cabeça."
    )

    assert result.requires_review is False
    assert result.matched_signals == []


def test_third_party_report_requires_review():
    result = analyze_text(
        "Minha mãe está com dor de cabeça."
    )

    assert result.requires_review is True
    assert any(
        finding["context"] == "third_party"
        for finding in result.findings
    )


def test_multiple_sentences_keep_separate_context():
    result = analyze_text(
        "Não preciso de ajuda. "
        "Estou com dor de cabeça."
    )

    assert "pain_report" in result.matched_signals
    assert "help_request" not in result.matched_signals
    assert result.requires_review is True
