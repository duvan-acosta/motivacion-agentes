"""Generación en lote — útil para producir packs de wallpapers para venta.

A diferencia de ``MotivacionWorkflow.run``, este flujo:

1. Salta el video, el audio TTS y el empaquetado por plataforma.
2. Solo ejecuta director → content → visual → wallpaper.
3. Rota temas (random o lista explícita) sin repetir si se solicita.
4. Escribe cada wallpaper en ``wallpapers/<batch_id>/wallpaper_NNN.jpg`` y
   un ``manifest.json`` con el tema, mensaje y timestamp por item.

Está pensado para producir lotes grandes (30-100 imágenes) de los que se
curan a mano las mejores para empaquetar como producto digital.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.content_creator import ContentCreatorAgent
from agents.director import DirectorAgent
from agents.visual_designer import VisualDesignerAgent
from pipelines.image_pipeline import ImagePipeline
from utils.config import ensure_dir, get_settings, load_yaml

logger = logging.getLogger(__name__)


def _default_themes() -> list[str]:
    brand = load_yaml("config/brand.yaml")
    themes = brand.get("content", {}).get("themes_rotation", [])
    if not themes:
        themes = ["resiliencia", "calma", "claridad", "propósito"]
    return list(themes)


def _theme_sequence(count: int, themes: list[str] | None) -> list[str]:
    """Devuelve ``count`` temas rotando equitativamente el catálogo."""
    pool = themes if themes else _default_themes()
    if not pool:
        return [""] * count
    # Rotación equitativa + shuffle dentro de cada bloque para evitar bloques
    # de un mismo tema seguidos.
    sequence: list[str] = []
    while len(sequence) < count:
        block = list(pool)
        random.shuffle(block)
        sequence.extend(block)
    return sequence[:count]


def run_wallpaper_batch(
    count: int,
    themes: list[str] | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Genera ``count`` wallpapers 4K vertical en un directorio nuevo.

    Devuelve un diccionario con metadatos del lote (path, items generados,
    items fallidos). No lanza excepción ante fallos individuales: los marca
    en el manifest para no abortar todo el batch.
    """
    if count < 1:
        raise ValueError("count debe ser >= 1")

    settings = get_settings()
    director = DirectorAgent()
    content = ContentCreatorAgent()
    visual = VisualDesignerAgent()
    images = ImagePipeline()

    batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
    base = ensure_dir((output_root or settings.project_root / "wallpapers") / batch_id)

    sequence = _theme_sequence(count, themes)
    items: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for i, theme in enumerate(sequence, start=1):
        try:
            plan = director.plan(theme or None)
            actual_theme = plan["theme"]
            content_result = content.generate(actual_theme, plan["content_id"])
            visual_spec = visual.design(
                actual_theme,
                content_result["message"],
                content_result.get("visual_keywords"),
            )
            wp_path = base / f"wallpaper_{i:03d}.jpg"
            images.generate_wallpaper(
                content_result["message"],
                actual_theme,
                visual_spec,
                wp_path,
            )
            items.append(
                {
                    "index": i,
                    "file": wp_path.name,
                    "theme": actual_theme,
                    "message": content_result["message"],
                    "content_id": plan["content_id"],
                }
            )
            logger.info("Wallpaper %d/%d (%s) listo", i, count, actual_theme)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falló wallpaper %d (%s): %s", i, theme, exc)
            failed.append({"index": i, "theme": theme, "error": str(exc)})

    manifest = {
        "batch_id": batch_id,
        "generated_at": datetime.now().isoformat(),
        "requested_count": count,
        "produced_count": len(items),
        "failed_count": len(failed),
        "items": items,
        "failed": failed,
    }
    (base / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "Batch %s: %d/%d wallpapers en %s",
        batch_id,
        len(items),
        count,
        base,
    )
    return {"batch_id": batch_id, "path": str(base), "manifest": manifest}
