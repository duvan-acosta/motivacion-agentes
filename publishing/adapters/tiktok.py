"""Adaptador TikTok Content Posting API (direct post de video, FILE_UPLOAD).

Flujo: (1) init de la publicación declarando tamaño y chunks, (2) subida del
binario al ``upload_url`` devuelto y (3) sondeo opcional del estado. Requiere una
app aprobada por TikTok y un ``access_token`` válido; si no, cae a manual.
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)

INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


class TikTokAdapter(BasePublisherAdapter):
    platform = "tiktok"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return self.settings.has_tiktok()

    def publish(self, package_path: Path) -> PublishResult:
        tt_dir = package_path / "tiktok"
        video = tt_dir / "video.mp4"

        if not video.exists():
            result = PublishResult(False, self.platform, "video.mp4 no encontrado", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "TikTok API no configurada (app aprobada + access token). Publicación manual.",
                manual=True,
            )
        else:
            result = self._do_publish(tt_dir, video)

        self.update_status(package_path, self.platform, result)
        return result

    def _do_publish(self, tt_dir: Path, video: Path) -> PublishResult:
        try:
            caption_path = tt_dir / "caption.txt"
            title = (
                caption_path.read_text(encoding="utf-8").strip()[:150]
                if caption_path.exists()
                else ""
            )
            video_size = video.stat().st_size

            publish_id, upload_url = self._init_upload(title, video_size)
            self._upload_video(upload_url, video, video_size)
            return PublishResult(
                True,
                self.platform,
                f"Enviado a TikTok (publish_id {publish_id}; revisar estado en la app)",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("TikTok publish error: %s", exc)
            return PublishResult(
                False, self.platform, f"Error API TikTok: {exc}. Usar carpeta manual.", manual=True
            )

    def _init_upload(self, title: str, video_size: int) -> tuple[str, str]:
        headers = {
            "Authorization": f"Bearer {self.settings.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        body = {
            "post_info": {
                "title": title,
                "privacy_level": "SELF_ONLY",
                "disable_comment": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        }
        resp = requests.post(INIT_URL, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not publish_id or not upload_url:
            raise RuntimeError(f"Respuesta init inesperada de TikTok: {resp.text[:200]}")
        return publish_id, upload_url

    def _upload_video(self, upload_url: str, video: Path, video_size: int) -> None:
        with video.open("rb") as f:
            data = f.read()
        headers = {
            "Content-Type": "video/mp4",
            "Content-Length": str(video_size),
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        }
        resp = requests.put(upload_url, headers=headers, data=data, timeout=600)
        resp.raise_for_status()
