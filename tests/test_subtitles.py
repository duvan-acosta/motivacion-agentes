"""Tests del módulo utils.subtitles."""

from __future__ import annotations

import pytest

from utils.subtitles import (
    MAX_CUE_DURATION,
    MIN_CUE_DURATION,
    Cue,
    _split_into_phrases,
    build_cues,
    cues_to_srt,
)


def test_split_respects_newlines():
    phrases = _split_into_phrases("Frase uno.\nFrase dos.\nFrase tres.")
    assert phrases == ["Frase uno.", "Frase dos.", "Frase tres."]


def test_split_breaks_long_phrase_by_punctuation():
    phrases = _split_into_phrases(
        "Algo importante. Otra cosa más larga; con varias partes."
    )
    # Debe partir por puntos al menos.
    assert "Algo importante." in phrases


def test_split_breaks_oversized_phrase_by_commas():
    # 13 palabras + comas → debe partir.
    long = "uno dos tres cuatro cinco, seis siete ocho nueve diez once doce trece"
    phrases = _split_into_phrases(long)
    assert all(len(p.split()) <= 12 for p in phrases)


def test_split_empty_returns_empty():
    assert _split_into_phrases("") == []
    assert _split_into_phrases("   \n  \n") == []


def test_build_cues_falls_back_to_estimate(monkeypatch, tmp_path):
    """Sin audio real, los cues se estiman por palabras × cadencia."""
    script = "Una frase corta.\nOtra un poco más larga.\nY un cierre."
    cues = build_cues(audio_path=None, script=script, fallback_duration=12.0)

    assert len(cues) == 3
    assert cues[0].start == 0.0
    # Cierra exactamente en el total.
    assert cues[-1].end == pytest.approx(12.0)
    # Las cues son consecutivas, sin solapamiento.
    for i in range(1, len(cues)):
        assert cues[i].start >= cues[i - 1].end - 0.01


def test_build_cues_respects_min_and_max_duration():
    # Una sola frase muy corta con duración total grande → MAX_CUE_DURATION.
    cues = build_cues(None, "Hola.", fallback_duration=30.0)
    # La única cue se extiende al total porque es la última.
    assert len(cues) == 1
    # Muchas frases con duración total muy pequeña → cada cue ≥ MIN_CUE_DURATION.
    short = "Una.\nDos.\nTres.\nCuatro.\nCinco.\nSeis."
    cues = build_cues(None, short, fallback_duration=2.0)
    # No debe haber cues de duración nula.
    assert all(c.duration > 0 for c in cues)


def test_build_cues_uses_word_count_as_fallback_when_no_duration():
    # 8 palabras / 2.2 wps ≈ 3.6s total
    cues = build_cues(None, "una dos tres cuatro cinco seis siete ocho.", fallback_duration=None)
    assert cues
    assert cues[-1].end > 0


def test_build_cues_handles_empty_script():
    assert build_cues(None, "", fallback_duration=10.0) == []
    assert build_cues(None, "   ", fallback_duration=10.0) == []


def test_build_cues_ignores_missing_audio_file(tmp_path):
    """Si el path de audio no existe, cae a estimación sin error."""
    cues = build_cues(
        audio_path=str(tmp_path / "no_existe.mp3"),
        script="Frase única.",
        fallback_duration=4.0,
    )
    assert cues
    assert cues[0].text == "Frase única."


def test_cues_to_srt_format():
    cues = [Cue("Hola mundo", 0.0, 2.5), Cue("Otra línea", 2.5, 5.0)]
    srt = cues_to_srt(cues)
    assert "1\n00:00:00,000 --> 00:00:02,500" in srt
    assert "Hola mundo" in srt
    assert "2\n00:00:02,500 --> 00:00:05,000" in srt


def test_cue_duration_property():
    cue = Cue("test", 1.0, 4.5)
    assert cue.duration == pytest.approx(3.5)


def test_whisper_called_only_for_audio_files(monkeypatch, tmp_path):
    """Solo invocamos Whisper si el archivo de audio tiene extensión válida."""
    txt = tmp_path / "not_audio.txt"
    txt.write_text("x")
    called = {"n": 0}

    def fake_transcribe(*args, **kwargs):
        called["n"] += 1
        return None

    monkeypatch.setattr("utils.subtitles._whisper_transcribe", fake_transcribe)
    build_cues(audio_path=str(txt), script="Hola.", fallback_duration=2.0)
    assert called["n"] == 0  # extension .txt → no se llama
