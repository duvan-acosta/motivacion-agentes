"""Stub adaptador X API v2."""

from __future__ import annotations

import logging
from pathlib import Path

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)


class TwitterAdapter(BasePublisherAdapter):
    platform = "twitter"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return bool(
            self.settings.x_api_key
            and self.settings.x_api_secret
            and self.settings.x_access_token
            and self.settings.x_access_token_secret
        )

    def publish(self, package_path: Path) -> PublishResult:
        image = package_path / "twitter" / "image.jpg"
        tweet = package_path / "twitter" / "tweet.txt"
        if not image.exists() or not tweet.exists():
            result = PublishResult(False, self.platform, "Archivos twitter incompletos", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "X API no configurada (plan de pago requerido). Publicación manual.",
                manual=True,
            )
        else:
            logger.info("X publish stub — pendiente integración API v2")
            result = PublishResult(
                False,
                self.platform,
                "Adaptador X en stub. Publicar manualmente desde carpeta twitter/.",
                manual=True,
            )

        self.update_status(package_path, self.platform, result)
        return result
