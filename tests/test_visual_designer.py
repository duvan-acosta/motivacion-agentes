"""Tests del VisualDesignerAgent — incluye la paleta HEX y los keywords."""

from __future__ import annotations


def test_design_returns_palette_for_known_theme(make_settings):
    make_settings(MOCK_MODE="true")
    from agents.visual_designer import VisualDesignerAgent

    agent = VisualDesignerAgent()
    spec = agent.design("calma", "Un mensaje")
    assert spec["palette"]["dominant"].startswith("#")
    assert spec["palette"]["accent"].startswith("#")
    assert spec["palette"]["shadow"].startswith("#")
    assert spec["theme"] == "calma"
    assert spec["search_keywords"]
    # Las keywords deben ir en inglés (para Pexels).
    keywords = " ".join(spec["search_keywords"]).lower()
    assert any(en in keywords for en in ["lake", "forest", "water", "mist"])


def test_design_unknown_theme_uses_defaults(make_settings):
    make_settings(MOCK_MODE="true")
    from agents.visual_designer import VisualDesignerAgent

    agent = VisualDesignerAgent()
    spec = agent.design("tema_inexistente", "Mensaje")
    assert spec["palette"]
    assert spec["search_keywords"]


def test_design_respects_explicit_keywords(make_settings):
    make_settings(MOCK_MODE="true")
    from agents.visual_designer import VisualDesignerAgent

    agent = VisualDesignerAgent()
    spec = agent.design("calma", "Mensaje", keywords=["custom kw", "second one"])
    assert spec["search_keywords"][:2] == ["custom kw", "second one"]
