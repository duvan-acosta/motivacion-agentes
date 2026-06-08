"""Adaptador Meta Graph API para Instagram/Facebook."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)


class MetaInstagramAdapter(BasePublisherAdapter):
    platform = "instagram"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return self.settings.has_meta()

    def publish(self, package_path: Path) -> PublishResult:
        if not self.can_publish():
            return PublishResult(
                success=False,
                platform=self.platform,
                message="Credenciales Meta no configuradas. Publicación manual requerida.",
                manual=True,
            )

        ig_dir = package_path / "instagram"
        image_path = ig_dir / "feed.jpg"
        caption_path = ig_dir / "caption.txt"
        hashtags_path = ig_dir / "hashtags.txt"

        if not image_path.exists():
            return PublishResult(False, self.platform, "feed.jpg no encontrado", manual=True)

        caption = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
        hashtags = hashtags_path.read_text(encoding="utf-8") if hashtags_path.exists() else ""
        full_caption = f"{caption}\n\n{hashtags}".strip()

        try:
            container_id = self._create_media_container(image_path, full_caption)
            if not container_id:
                raise RuntimeError("No se pudo crear contenedor de media")

            published = self._publish_container(container_id)
            if published:
                result = PublishResult(True, self.platform, "Publicado en Instagram vía Graph API")
            else:
                result = PublishResult(
                    False, self.platform, "Fallo al publicar contenedor", manual=True
                )
        except Exception as exc:
            logger.error("Meta publish error: %s", exc)
            result = PublishResult(
                False, self.platform, f"Error API Meta: {exc}. Usar carpeta manual.", manual=True
            )

        self.update_status(package_path, self.platform, result)
        return result

    def _create_media_container(self, image_path: Path, caption: str) -> str | None:
        account_id = self.settings.meta_instagram_account_id
        token = self.settings.meta_access_token
        url = f"https://graph.facebook.com/v19.0/{account_id}/media"

        with image_path.open("rb") as f:
            # Para producción real se sube a URL pública primero; aquí simulamos intento
            pass

        # Graph API requiere image_url pública; documentamos fallback manual
        params = {
            "caption": caption[:2200],
            "access_token": token,
        }
        resp = requests.post(url, data=params, timeout=30)
        if resp.status_code == 400:
            logger.info("Meta API requiere image_url pública — fallback manual")
            return None
        resp.raise_for_status()
        return resp.json().get("id")

    def _publish_container(self, container_id: str) -> bool:
        account_id = self.settings.meta_instagram_account_id
        token = self.settings.meta_access_token
        url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
        resp = requests.post(
            url,
            data={"creation_id": container_id, "access_token": token},
            timeout=30,
        )
        return resp.status_code == 200

    def publish_facebook(self, package_path: Path) -> PublishResult:
        if not self.settings.has_meta():
            return PublishResult(False, "facebook", "Credenciales Meta no configuradas", manual=True)
        fb_dir = package_path / "facebook"
        if not (fb_dir / "post.jpg").exists():
            return PublishResult(False, "facebook", "post.jpg no encontrado", manual=True)
        result = PublishResult(
            False,
            "facebook",
            "Facebook Graph API requiere configuración adicional. Usar publicación manual.",
            manual=True,
        )
        self.update_status(package_path, "facebook", result)
        return result
