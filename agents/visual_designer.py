"""VisualDesignerAgent — fondo, tipografía y composición."""

from __future__ import annotations

import logging
from typing import Any

from rag.store import get_rag_store
from utils.config import get_settings, load_yaml

logger = logging.getLogger(__name__)

THEME_KEYWORDS = {
    "resiliencia": ["mountain peak", "storm clearing", "rocky cliff"],
    "calma": ["calm ocean", "peaceful lake", "misty forest"],
    "claridad": ["sunrise", "golden hour", "open sky"],
    "propósito": ["path forest", "compass", "horizon road"],
    "gratitud": ["sunset", "flower field", "warm light"],
    "presencia": ["zen garden", "rain drops", "single tree"],
    "coraje": ["ocean waves", "eagle flight", "lightning distant"],
    "sabiduría": ["ancient tree", "stars night", "old library"],
}


class VisualDesignerAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rag = get_rag_store()
        self.brand = load_yaml("config/brand.yaml")

    def design(self, theme: str, message: str, keywords: list[str] | None = None) -> dict[str, Any]:
        visual_ctx = self.rag.query("visual", f"tema {theme} composición fondo")
        kw = keywords or THEME_KEYWORDS.get(theme, ["nature peaceful", "landscape calm"])
        if not keywords:
            kw = THEME_KEYWORDS.get(theme, kw)

        visual_config = self.brand.get("visual", {})
        return {
            "theme": theme,
            "message": message,
            "search_keywords": kw[:3],
            "visual_context": visual_ctx[:2],
            "font_family": visual_config.get("font_family", "Playfair Display"),
            "fallback_font": visual_config.get("fallback_font", "DejaVu Serif"),
            "text_color": visual_config.get("text_color", "#FFFFFF"),
            "gradient_opacity": visual_config.get("gradient_opacity", 0.55),
            "max_lines": visual_config.get("max_message_lines", 6),
        }
