"""Adaptador Pinterest — crea un Pin vía API v5.

Pinterest es el canal de monetización más temprana del proyecto: cada Pin lleva
un **link de destino** directo a la tienda y se descubre por búsqueda (no por
seguidores), así que un Pin nuevo genera tráfico con intención de compra desde
el primer día.

Ventaja técnica frente a Meta: la API v5 acepta la imagen **en base64** dentro
del propio request (``source_type: image_base64``), por lo que **no requiere un
media host público**. Reutiliza la imagen vertical con frase que el sistema ya
genera para Instagram (``instagram/feed.jpg``).

El link del Pin se construye con UTM por plataforma a partir del producto activo
(``config/products.yaml``); si no hay producto activo, el Pin se publica sin link.

Sin credenciales (``PINTEREST_ACCESS_TOKEN`` + ``PINTEREST_BOARD_ID``) cae a
publicación manual, igual que el resto de adaptadores.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings
from utils.pinterest_auth import resolve_access_token
from utils.products import build_tracked_url, get_active_product

logger = logging.getLogger(__name__)

PINS_URL = "https://api.pinterest.com/v5/pins"

# Límites de la API v5.
TITLE_MAX = 100
DESCRIPTION_MAX = 800


class PinterestAdapter(BasePublisherAdapter):
    platform = "pinterest"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return self.settings.has_pinterest()

    def publish(self, package_path: Path) -> PublishResult:
        # Reutiliza el asset vertical con frase que ya se genera para Instagram.
        ig_dir = package_path / "instagram"
        image = ig_dir / "feed.jpg"
        caption = ig_dir / "caption.txt"
        hashtags = ig_dir / "hashtags.txt"

        if not image.exists():
            result = PublishResult(
                False, self.platform, "feed.jpg no encontrado para el Pin", manual=True
            )
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "Pinterest no configurado (PINTEREST_ACCESS_TOKEN + "
                "PINTEREST_BOARD_ID requeridos). Publicación manual.",
                manual=True,
            )
        else:
            result = self._do_publish(package_path, image, caption, hashtags)

        self.update_status(package_path, self.platform, result)
        return result

    def _build_title(self, package_path: Path, caption_text: str) -> str:
        """Título del Pin: el mensaje motivacional, o la 1ª línea del caption."""
        message_file = package_path / "source" / "message.txt"
        if message_file.exists():
            title = message_file.read_text(encoding="utf-8").strip()
        else:
            title = caption_text.strip().splitlines()[0] if caption_text.strip() else ""
        return title[:TITLE_MAX]

    def _build_link(self, package_path: Path) -> str | None:
        """Link de destino del Pin = producto activo + UTM de Pinterest."""
        product = get_active_product()
        if not product:
            return None
        return build_tracked_url(product.url, self.platform, content_id=package_path.name)

    def _do_publish(
        self, package_path: Path, image: Path, caption: Path, hashtags: Path
    ) -> PublishResult:
        try:
            token = resolve_access_token(self.settings)
            if not token:
                raise RuntimeError("No se pudo resolver el access token de Pinterest")

            caption_text = caption.read_text(encoding="utf-8") if caption.exists() else ""
            hashtags_text = hashtags.read_text(encoding="utf-8") if hashtags.exists() else ""
            description = f"{caption_text}\n\n{hashtags_text}".strip()[:DESCRIPTION_MAX]
            title = self._build_title(package_path, caption_text)

            image_b64 = base64.b64encode(image.read_bytes()).decode("ascii")
            payload: dict = {
                "board_id": self.settings.pinterest_board_id,
                "title": title,
                "description": description,
                "media_source": {
                    "source_type": "image_base64",
                    "content_type": "image/jpeg",
                    "data": image_b64,
                },
            }
            link = self._build_link(package_path)
            if link:
                payload["link"] = link

            resp = requests.post(
                PINS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=60,
            )
            resp.raise_for_status()
            pin_id = resp.json().get("id")
            return PublishResult(True, self.platform, f"Publicado en Pinterest (pin {pin_id})")
        except Exception as exc:  # noqa: BLE001
            logger.error("Pinterest publish error: %s", exc)
            return PublishResult(
                False,
                self.platform,
                f"Error API Pinterest: {exc}. Usar carpeta manual.",
                manual=True,
            )
