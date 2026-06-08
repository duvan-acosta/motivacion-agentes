"""Stub adaptador YouTube Data API v3."""

from __future__ import annotations

import logging
from pathlib import Path

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)


class YouTubeAdapter(BasePublisherAdapter):
    platform = "youtube"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return bool(
            self.settings.youtube_client_id
            and self.settings.youtube_client_secret
            and self.settings.youtube_refresh_token
        )

    def publish(self, package_path: Path) -> PublishResult:
        short = package_path / "youtube" / "short.mp4"
        if not short.exists():
            result = PublishResult(False, self.platform, "short.mp4 no encontrado", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "YouTube OAuth no configurado. Publicación manual requerida.",
                manual=True,
            )
        else:
            logger.info("YouTube publish stub — pendiente OAuth upload")
            result = PublishResult(
                False,
                self.platform,
                "Adaptador YouTube en stub. Subir manualmente desde carpeta youtube/.",
                manual=True,
            )

        self.update_status(package_path, self.platform, result)
        return result
