"""Stub adaptador TikTok Content Posting API."""

from __future__ import annotations

import logging
from pathlib import Path

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)


class TikTokAdapter(BasePublisherAdapter):
    platform = "tiktok"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return bool(self.settings.tiktok_access_token and self.settings.tiktok_client_key)

    def publish(self, package_path: Path) -> PublishResult:
        video = package_path / "tiktok" / "video.mp4"
        if not video.exists():
            result = PublishResult(False, self.platform, "video.mp4 no encontrado", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "TikTok API no configurada. App aprobada requerida. Publicación manual.",
                manual=True,
            )
        else:
            # Stub: integración real con TikTok Content Posting API
            logger.info("TikTok publish stub — pendiente integración API")
            result = PublishResult(
                False,
                self.platform,
                "Adaptador TikTok en stub. Subir manualmente desde carpeta tiktok/.",
                manual=True,
            )

        self.update_status(package_path, self.platform, result)
        return result
