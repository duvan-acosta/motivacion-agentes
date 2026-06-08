"""Adaptador X (Twitter) — subida de media v1.1 + creación de tweet v2.

La autenticación es OAuth 1.0a (user context), que requiere firmar las peticiones.
Se usa ``requests_oauthlib`` (dependencia ligera). Si no está instalada o las
credenciales fallan, cae a publicación manual.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)

MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEETS_URL = "https://api.twitter.com/2/tweets"


class TwitterAdapter(BasePublisherAdapter):
    platform = "twitter"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return self.settings.has_x()

    def publish(self, package_path: Path) -> PublishResult:
        tw_dir = package_path / "twitter"
        image = tw_dir / "image.jpg"
        tweet = tw_dir / "tweet.txt"

        if not image.exists() or not tweet.exists():
            result = PublishResult(False, self.platform, "Archivos twitter incompletos", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "X API no configurada (claves OAuth 1.0a requeridas). Publicación manual.",
                manual=True,
            )
        else:
            result = self._do_publish(image, tweet)

        self.update_status(package_path, self.platform, result)
        return result

    def _build_auth(self):
        try:
            from requests_oauthlib import OAuth1  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError(
                "requests-oauthlib no está instalado (pip install requests-oauthlib)"
            ) from exc
        return OAuth1(
            self.settings.x_api_key,
            self.settings.x_api_secret,
            self.settings.x_access_token,
            self.settings.x_access_token_secret,
        )

    def _do_publish(self, image: Path, tweet: Path) -> PublishResult:
        try:
            auth = self._build_auth()
            text = tweet.read_text(encoding="utf-8").strip()[:280]
            media_id = self._upload_media(auth, image)

            payload: dict = {"text": text}
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

            resp = requests.post(TWEETS_URL, json=payload, auth=auth, timeout=60)
            resp.raise_for_status()
            tweet_id = resp.json().get("data", {}).get("id")
            return PublishResult(True, self.platform, f"Publicado en X (tweet {tweet_id})")
        except Exception as exc:  # noqa: BLE001
            logger.error("X publish error: %s", exc)
            return PublishResult(
                False, self.platform, f"Error API X: {exc}. Usar carpeta manual.", manual=True
            )

    def _upload_media(self, auth, image: Path) -> str | None:
        with image.open("rb") as f:
            resp = requests.post(
                MEDIA_UPLOAD_URL, files={"media": f}, auth=auth, timeout=120
            )
        resp.raise_for_status()
        return resp.json().get("media_id_string")
