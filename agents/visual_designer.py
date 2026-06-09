"""VisualDesignerAgent — fondo, tipografía y composición."""

from __future__ import annotations

import logging
from typing import Any

from rag.store import get_rag_store
from utils.config import get_settings, load_yaml

logger = logging.getLogger(__name__)

THEME_KEYWORDS = {
    # Temas reflexivos clásicos
    "resiliencia": ["mountain peak fog", "storm clearing", "rocky coast"],
    "calma": ["calm lake mist", "foggy forest dawn", "still water"],
    "claridad": ["sunrise horizon", "golden hour field", "open sky"],
    "propósito": ["forest path morning", "distant lighthouse", "country road"],
    "proposito": ["forest path morning", "distant lighthouse", "country road"],
    "gratitud": ["warm sunset", "wildflowers backlit", "tea morning"],
    "presencia": ["raindrops window", "single tree field", "zen garden"],
    "coraje": ["ocean storm waves", "eagle flight", "distant lightning"],
    "sabiduría": ["starry sky milky way", "ancient tree", "old books"],
    "sabiduria": ["starry sky milky way", "ancient tree", "old books"],
    # Temas motivacionales nuevos (foco psicología práctica)
    "esperanza": ["sunrise dawn light", "warm sky", "fresh morning"],
    "amor_propio": ["self care moment", "warm bath light", "candle morning"],
    "empezar_de_nuevo": ["sunrise road", "open field", "new path"],
    "ansiedad_cotidiana": ["evening sky calm", "hand on heart", "soft breath"],
    "autoestima": ["confident portrait sunset", "woman looking up", "self portrait warm"],
    "soledad_saludable": ["person reading window", "solo coffee morning", "quiet apartment light"],
    "limites": ["closed window light", "open hand stop", "boundary fence sunset"],
    "limites_saludables": ["closed window light", "open hand stop", "boundary fence sunset"],
}

# Paletas HEX por tema (sincronizadas con rag/knowledge/temas-visuales.md).
THEME_PALETTES: dict[str, dict[str, str]] = {
    "resiliencia": {"dominant": "#1F2A38", "accent": "#C29A55", "shadow": "#0B1117"},
    "calma": {"dominant": "#2C4A52", "accent": "#A8C5C0", "shadow": "#10202A"},
    "claridad": {"dominant": "#E6C893", "accent": "#FFFFFF", "shadow": "#3B2F1F"},
    "propósito": {"dominant": "#3E5641", "accent": "#D7B27B", "shadow": "#1A2519"},
    "proposito": {"dominant": "#3E5641", "accent": "#D7B27B", "shadow": "#1A2519"},
    "gratitud": {"dominant": "#C57B57", "accent": "#F5E6CA", "shadow": "#5C3A28"},
    "presencia": {"dominant": "#2A2D34", "accent": "#9BA9B4", "shadow": "#13151B"},
    "coraje": {"dominant": "#3C1F2B", "accent": "#D88C5A", "shadow": "#1A0C13"},
    "sabiduría": {"dominant": "#1A2238", "accent": "#9DAAF2", "shadow": "#0A0E1A"},
    "sabiduria": {"dominant": "#1A2238", "accent": "#9DAAF2", "shadow": "#0A0E1A"},
    # Paletas cálidas para los temas motivacionales nuevos
    "esperanza": {"dominant": "#E89B5A", "accent": "#FFE4C7", "shadow": "#5C3520"},
    "amor_propio": {"dominant": "#D17A8F", "accent": "#F8E0DD", "shadow": "#5A2A36"},
    "empezar_de_nuevo": {"dominant": "#E6B466", "accent": "#FFF4DA", "shadow": "#4A331A"},
    "ansiedad_cotidiana": {"dominant": "#5E7A8C", "accent": "#C9D6DE", "shadow": "#1F2E38"},
    "autoestima": {"dominant": "#B26B4F", "accent": "#F0D2BB", "shadow": "#3D1F12"},
    "soledad_saludable": {"dominant": "#4A6373", "accent": "#B7C8D2", "shadow": "#1A2730"},
    "limites": {"dominant": "#7D4A4A", "accent": "#E0B8B8", "shadow": "#2E1818"},
    "limites_saludables": {"dominant": "#7D4A4A", "accent": "#E0B8B8", "shadow": "#2E1818"},
}

DEFAULT_PALETTE = {"dominant": "#2A2D34", "accent": "#9BA9B4", "shadow": "#13151B"}


class VisualDesignerAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rag = get_rag_store()
        self.brand = load_yaml("config/brand.yaml")

    def design(self, theme: str, message: str, keywords: list[str] | None = None) -> dict[str, Any]:
        visual_ctx = self.rag.query(
            "visual", f"{theme} paleta composición fondo tipografía safe zone"
        )

        # Las visual_keywords del ContentCreator (en inglés) tienen prioridad; si no,
        # caemos al mapeo por tema y, por último, a un default neutro.
        kw = keywords if keywords else THEME_KEYWORDS.get(theme, ["nature peaceful", "landscape calm"])
        palette = THEME_PALETTES.get(theme, DEFAULT_PALETTE)
        visual_config = self.brand.get("visual", {})

        return {
            "theme": theme,
            "message": message,
            "search_keywords": kw[:3],
            "visual_context": visual_ctx[:3],
            "palette": palette,
            "font_family": visual_config.get("font_family", "Playfair Display"),
            "fallback_font": visual_config.get("fallback_font", "DejaVu Serif"),
            "text_color": visual_config.get("text_color", "#FFFFFF"),
            "gradient_opacity": visual_config.get("gradient_opacity", 0.55),
            "max_lines": visual_config.get("max_message_lines", 6),
        }
