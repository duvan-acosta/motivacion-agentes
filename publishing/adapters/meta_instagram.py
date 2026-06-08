"""Adaptador Meta Graph API para Instagram/Facebook.

La Graph API publica contenido en dos pasos: (1) crear un *contenedor* de media
referenciando una **URL pública** del archivo y (2) publicar ese contenedor. Por
eso este adaptador necesita un ``MediaHost`` que exponga la imagen/video en una
URL accesible. Sin hosting configurado, cae a publicación manual.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from publishing.media_host import MediaHost, get_media_host
from utils.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


class MetaInstagramAdapter(BasePublisherAdapter):
    platform = "instagram"

    def __init__(self, media_host: MediaHost | None = None) -> None:
        self.settings = get_settings()
        self.media_host = media_host or get_media_host()

    def can_publish(self) -> bool:
        return self.settings.has_meta()

    def publish(self, package_path: Path) -> PublishResult:
        if not self.can_publish():
            result = PublishResult(
                success=False,
                platform=self.platform,
                message="Credenciales Meta no configuradas. Publicación manual requerida.",
                manual=True,
            )
            self.update_status(package_path, self.platform, result)
            return result

        ig_dir = package_path / "instagram"
        image_path = ig_dir / "feed.jpg"
        caption_path = ig_dir / "caption.txt"
        hashtags_path = ig_dir / "hashtags.txt"

        if not image_path.exists():
            result = PublishResult(False, self.platform, "feed.jpg no encontrado", manual=True)
            self.update_status(package_path, self.platform, result)
            return result

        if not self.media_host.available():
            result = PublishResult(
                False,
                self.platform,
                "Sin hosting público de media (MEDIA_HOST_PROVIDER). "
                "Graph API requiere image_url pública. Publicación manual.",
                manual=True,
            )
            self.update_status(package_path, self.platform, result)
            return result

        caption = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
        hashtags = hashtags_path.read_text(encoding="utf-8") if hashtags_path.exists() else ""
        full_caption = f"{caption}\n\n{hashtags}".strip()[:2200]

        try:
            image_url = self.media_host.upload(image_path)
            if not image_url:
                raise RuntimeError("El media host no devolvió URL pública")

            container_id = self._create_image_container(image_url, full_caption)
            if not container_id:
                raise RuntimeError("No se pudo crear el contenedor de media")

            self._wait_until_ready(container_id)
            published_id = self._publish_container(container_id)
            if published_id:
                result = PublishResult(
                    True,
                    self.platform,
                    f"Publicado en Instagram (media id {published_id})",
                )
            else:
                result = PublishResult(
                    False, self.platform, "Fallo al publicar el contenedor", manual=True
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("Meta publish error: %s", exc)
            result = PublishResult(
                False, self.platform, f"Error API Meta: {exc}. Usar carpeta manual.", manual=True
            )

        self.update_status(package_path, self.platform, result)
        return result

    def _create_image_container(self, image_url: str, caption: str) -> str | None:
        account_id = self.settings.meta_instagram_account_id
        token = self.settings.meta_access_token
        resp = requests.post(
            f"{GRAPH_BASE}/{account_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id")

    def _wait_until_ready(self, container_id: str, attempts: int = 5, delay: float = 2.0) -> None:
        """Sondea el estado del contenedor hasta que esté FINISHED (relevante en Reels)."""
        token = self.settings.meta_access_token
        for _ in range(attempts):
            resp = requests.get(
                f"{GRAPH_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=30,
            )
            if resp.status_code != 200:
                return
            status_code = resp.json().get("status_code")
            if status_code in (None, "FINISHED"):
                return
            if status_code == "ERROR":
                raise RuntimeError("El contenedor de media devolvió status ERROR")
            time.sleep(delay)

    def _publish_container(self, container_id: str) -> str | None:
        account_id = self.settings.meta_instagram_account_id
        token = self.settings.meta_access_token
        resp = requests.post(
            f"{GRAPH_BASE}/{account_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("id")

    def publish_facebook(self, package_path: Path) -> PublishResult:
        """Publica una foto en una Página de Facebook vía Graph API.

        Usa el endpoint ``/{page_id}/photos`` con ``url`` pública del media host.
        """
        if not self.settings.has_meta() or not self.settings.meta_facebook_page_id:
            result = PublishResult(
                False,
                "facebook",
                "Credenciales/Page ID de Facebook no configuradas. Publicación manual.",
                manual=True,
            )
            self.update_status(package_path, "facebook", result)
            return result

        fb_dir = package_path / "facebook"
        image_path = fb_dir / "post.jpg"
        caption_path = fb_dir / "caption.txt"
        if not image_path.exists():
            result = PublishResult(False, "facebook", "post.jpg no encontrado", manual=True)
            self.update_status(package_path, "facebook", result)
            return result

        if not self.media_host.available():
            result = PublishResult(
                False,
                "facebook",
                "Sin hosting público de media (MEDIA_HOST_PROVIDER). Publicación manual.",
                manual=True,
            )
            self.update_status(package_path, "facebook", result)
            return result

        caption = caption_path.read_text(encoding="utf-8") if caption_path.exists() else ""
        try:
            image_url = self.media_host.upload(image_path)
            if not image_url:
                raise RuntimeError("El media host no devolvió URL pública")
            resp = requests.post(
                f"{GRAPH_BASE}/{self.settings.meta_facebook_page_id}/photos",
                data={
                    "url": image_url,
                    "caption": caption,
                    "access_token": self.settings.meta_access_token,
                },
                timeout=60,
            )
            resp.raise_for_status()
            post_id = resp.json().get("post_id") or resp.json().get("id")
            result = PublishResult(True, "facebook", f"Publicado en Facebook ({post_id})")
        except Exception as exc:  # noqa: BLE001
            logger.error("Facebook publish error: %s", exc)
            result = PublishResult(
                False, "facebook", f"Error API Facebook: {exc}. Usar carpeta manual.", manual=True
            )

        self.update_status(package_path, "facebook", result)
        return result
