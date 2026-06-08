"""Pipeline de imágenes: Pexels + Pillow → multi-plataforma."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from utils.config import ensure_dir, get_settings
from utils.media import (
    create_gradient_background,
    fetch_pexels_photo,
    render_text_overlay,
    resize_cover,
)

logger = logging.getLogger(__name__)

EXPORTS = {
    "instagram_feed": (1080, 1080),
    "facebook_post": (1080, 1080),
    "twitter_image": (1200, 675),
    "youtube_thumb": (1280, 720),
}


class ImagePipeline:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.output_dir = output_dir or ensure_dir(self.settings.project_root / "tmp" / "images")

    def generate(self, message: str, theme: str, visual_spec: dict[str, Any]) -> dict[str, str]:
        keywords = visual_spec.get("search_keywords", [theme])
        base_bg = fetch_pexels_photo(keywords)
        if base_bg is None:
            logger.info("Usando fondo gradiente (Pexels no disponible)")
            base_bg = create_gradient_background(1920, 1080, theme)

        master = render_text_overlay(base_bg, message, visual_spec)
        results: dict[str, str] = {}

        for name, (w, h) in EXPORTS.items():
            out_path = self.output_dir / f"{name}.jpg"
            sized = resize_cover(master, w, h)
            sized.save(out_path, "JPEG", quality=92)
            results[name] = str(out_path)
            logger.info("Imagen exportada: %s (%dx%d)", name, w, h)

        return results
