
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
