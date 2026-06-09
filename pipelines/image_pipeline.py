"""Pipeline de imágenes: Pexels + Pillow → multi-plataforma."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from utils.config import ensure_dir, get_settings, load_yaml
from utils.media import (
    create_gradient_background,
    fetch_pexels_photo,
    render_text_overlay,
    render_wallpaper_overlay,
    resize_cover,
)

logger = logging.getLogger(__name__)

EXPORTS = {
    "instagram_feed": (1080, 1080),
    "facebook_post": (1080, 1080),
    "twitter_image": (1200, 675),
    "youtube_thumb": (1280, 720),
}

# Wallpaper móvil 4K vertical — cubre hasta iPhone 15 Pro Max (1290×2796)
# y Android flagship sin pérdida de calidad.
WALLPAPER_4K_VERTICAL = (2160, 3840)


class ImagePipeline:
    def __init__(self, output_dir: Path | None = None) -> None:
        self.settings = get_settings()
        self.output_dir = output_dir or ensure_dir(self.settings.project_root / "tmp" / "images")

    def generate(self, message: str, theme: str, visual_spec: dict[str, Any]) -> dict[str, str]:
        """Genera todos los formatos de imagen para redes sociales.

        Antes el flujo era: 1 render de texto en master 1920×1080 → resize_cover
        a cada formato. Eso recortaba los bordes y dejaba texto incompleto en
        feed cuadrado (1080×1080).

        Ahora: descarga UNA foto de Pexels grande, y para cada formato hace
        resize_cover de la foto a las dimensiones del formato + render del
        texto con el wrap correcto para ese lienzo. Sin recortes raros.
        """
        keywords = visual_spec.get("search_keywords", [theme])
        # Pedimos foto grande para que cualquier resize_cover tenga material.
        base_bg = fetch_pexels_photo(keywords, width=1920, height=1920)
        if base_bg is None:
            logger.info("Usando fondo gradiente (Pexels no disponible)")
            base_bg = create_gradient_background(1920, 1920, theme)

        results: dict[str, str] = {}
        for name, (w, h) in EXPORTS.items():
            sized_bg = resize_cover(base_bg, w, h)
            rendered = render_text_overlay(sized_bg, message, visual_spec)
            out_path = self.output_dir / f"{name}.jpg"
            rendered.save(out_path, "JPEG", quality=92)
            results[name] = str(out_path)
            logger.info("Imagen exportada: %s (%dx%d)", name, w, h)

        return results

    def generate_wallpaper(
        self,
        message: str,
        theme: str,
        visual_spec: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Genera un wallpaper móvil 4K vertical (2160×3840) listo para empaquetar.

        Hace el render del overlay directamente sobre un lienzo vertical para
        que la tipografía respete las proporciones (sin upscale desde 1080).
        """
        w, h = WALLPAPER_4K_VERTICAL
        keywords = visual_spec.get("search_keywords", [theme])

        # Pexels devuelve apaisado por defecto; intentamos primero un fondo
        # vertical recortando. Si no hay Pexels, gradiente nativo del tamaño.
        base_bg = fetch_pexels_photo(keywords, width=w, height=h)
        if base_bg is None:
            base_bg = create_gradient_background(w, h, theme)
        else:
            base_bg = resize_cover(base_bg, w, h)

        brand_name = (
            load_yaml("config/brand.yaml").get("brand", {}).get("display_name")
            or "Mental Equilibrio"
        )
        master = render_wallpaper_overlay(base_bg, message, visual_spec, brand_name)

        # Aseguramos exactamente el tamaño solicitado (por si overlay alteró).
        if master.size != (w, h):
            master = resize_cover(master, w, h)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        master.save(output_path, "JPEG", quality=92)
        logger.info("Wallpaper 4K exportado: %s (%dx%d)", output_path.name, w, h)
        return output_path
