"""Agente publicador via navegador — orquesta Instagram, TikTok y Facebook."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from utils.config import get_settings

logger = logging.getLogger(__name__)


class BrowserPublisherAgent:
    """Publica en RRSS usando Playwright sin depender de APIs oficiales."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_publishers(self) -> dict[str, Any]:
        from publishing.browser.facebook import FacebookBrowserPublisher
        from publishing.browser.instagram import InstagramBrowserPublisher
        from publishing.browser.tiktok import TikTokBrowserPublisher
        from publishing.browser.twitter import TwitterBrowserPublisher
        from publishing.browser.youtube import YouTubeBrowserPublisher

        return {
            "instagram": InstagramBrowserPublisher(),
            "tiktok": TikTokBrowserPublisher(),
            "facebook": FacebookBrowserPublisher(),
            "twitter": TwitterBrowserPublisher(),
            "youtube": YouTubeBrowserPublisher(),
        }

    def publish(
        self,
        package_path: str | Path,
        platforms: list[str] | None = None,
    ) -> dict[str, Any]:
        path = Path(package_path)
        if not path.exists():
            return {"success": False, "error": f"Paquete no encontrado: {path}"}

        publishers = self._get_publishers()
        targets = platforms or list(publishers.keys())
        results: dict[str, Any] = {}
        published: list[str] = []

        for name in targets:
            pub = publishers.get(name)
            if not pub:
                logger.warning("[browser_publisher] Plataforma no soportada: %s", name)
                continue
            try:
                logger.info("[browser_publisher] Publicando en %s...", name)
                result = pub.publish(path)
                results[name] = result
                if result.get("success"):
                    published.append(name)
                    logger.info("[browser_publisher] %s — OK", name)
                else:
                    logger.warning(
                        "[browser_publisher] %s — fallido: %s",
                        name,
                        result.get("error", "desconocido"),
                    )
            except Exception as exc:
                results[name] = {"success": False, "error": str(exc)}
                logger.error("[browser_publisher] Error inesperado en %s: %s", name, exc)

        return {
            "success": bool(published),
            "published": published,
            "results": results,
        }
