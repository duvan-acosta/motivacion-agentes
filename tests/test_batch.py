"""Tests del comando batch y del export wallpaper 4K."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_theme_sequence_rotates_uniformly(make_settings):
    make_settings()
    from graph.batch import _theme_sequence

    seq = _theme_sequence(8, ["calma", "claridad"])
    assert len(seq) == 8
    # Cada tema aparece exactamente 4 veces.
    assert seq.count("calma") == 4
    assert seq.count("claridad") == 4


def test_theme_sequence_uses_defaults_when_none(make_settings):
    make_settings()
    from graph.batch import _theme_sequence

    seq = _theme_sequence(5, None)
    assert len(seq) == 5
    assert all(t for t in seq)


def test_wallpaper_pipeline_method_writes_4k_file(make_settings, tmp_path):
    """ImagePipeline.generate_wallpaper produce un JPG 2160×3840."""
    make_settings()
    from PIL import Image as PILImage
    from pipelines.image_pipeline import ImagePipeline, WALLPAPER_4K_VERTICAL

    pipe = ImagePipeline(output_dir=tmp_path)
    spec = {
        "search_keywords": ["calm"],
        "font_family": "DejaVu Serif",
        "fallback_font": "DejaVu Serif",
        "text_color": "#FFFFFF",
        "gradient_opacity": 0.55,
        "max_lines": 6,
    }
    out = pipe.generate_wallpaper(
        "Una frase corta para wallpaper.",
        "calma",
        spec,
        tmp_path / "wp.jpg",
    )
    assert out.exists()
    with PILImage.open(out) as img:
        assert img.size == WALLPAPER_4K_VERTICAL


def test_batch_produces_requested_count_and_manifest(make_settings, tmp_path):
    """run_wallpaper_batch genera N imágenes + manifest válido en modo demo."""
    make_settings(MOCK_MODE="true", DEMO_MODE="true")
    from graph.batch import run_wallpaper_batch

    result = run_wallpaper_batch(3, themes=["calma"], output_root=tmp_path)
    batch_dir = Path(result["path"])
    assert batch_dir.exists()

    files = sorted(batch_dir.glob("wallpaper_*.jpg"))
    assert len(files) == 3

    manifest = json.loads((batch_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["produced_count"] == 3
    assert manifest["requested_count"] == 3
    assert manifest["failed_count"] == 0
    assert all(item["theme"] == "calma" for item in manifest["items"])
    assert all("message" in item for item in manifest["items"])


def test_batch_rotates_multiple_themes(make_settings, tmp_path):
    make_settings(MOCK_MODE="true", DEMO_MODE="true")
    from graph.batch import run_wallpaper_batch

    result = run_wallpaper_batch(
        4, themes=["calma", "claridad"], output_root=tmp_path
    )
    themes_used = {item["theme"] for item in result["manifest"]["items"]}
    assert themes_used == {"calma", "claridad"}


def test_batch_rejects_invalid_count(make_settings, tmp_path):
    make_settings(MOCK_MODE="true", DEMO_MODE="true")
    from graph.batch import run_wallpaper_batch

    with pytest.raises(ValueError):
        run_wallpaper_batch(0, output_root=tmp_path)


def test_batch_isolates_failures(make_settings, tmp_path, monkeypatch):
    """Si una iteración falla, las demás continúan y queda en failed."""
    make_settings(MOCK_MODE="true", DEMO_MODE="true")
    from graph import batch as batch_mod

    original = batch_mod.ImagePipeline.generate_wallpaper
    calls = {"n": 0}

    def flaky(self, message, theme, spec, output_path):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("fallo simulado")
        return original(self, message, theme, spec, output_path)

    monkeypatch.setattr(batch_mod.ImagePipeline, "generate_wallpaper", flaky)
    result = batch_mod.run_wallpaper_batch(3, themes=["calma"], output_root=tmp_path)

    assert result["manifest"]["produced_count"] == 2
    assert result["manifest"]["failed_count"] == 1
    assert "fallo simulado" in result["manifest"]["failed"][0]["error"]
