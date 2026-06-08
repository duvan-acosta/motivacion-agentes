"""Adaptador YouTube Data API v3 (Shorts) con OAuth refresh + upload reanudable."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from publishing.base_adapter import BasePublisherAdapter, PublishResult
from utils.config import get_settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeAdapter(BasePublisherAdapter):
    platform = "youtube"

    def __init__(self) -> None:
        self.settings = get_settings()

    def can_publish(self) -> bool:
        return self.settings.has_youtube()

    def publish(self, package_path: Path) -> PublishResult:
        yt_dir = package_path / "youtube"
        short = yt_dir / "short.mp4"

        if not short.exists():
            result = PublishResult(False, self.platform, "short.mp4 no encontrado", manual=True)
        elif not self.can_publish():
            result = PublishResult(
                False,
                self.platform,
                "YouTube OAuth no configurado (client id/secret/refresh token). Publicación manual.",
                manual=True,
            )
        else:
            result = self._do_publish(yt_dir, short)

        self.update_status(package_path, self.platform, result)
        return result

    def _do_publish(self, yt_dir: Path, video: Path) -> PublishResult:
        try:
            access_token = self._refresh_access_token()
            title = self._read(yt_dir / "title.txt", "Reflexión")
            description = self._read(yt_dir / "description.txt", "")
            tags_raw = self._read(yt_dir / "tags.txt", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

            metadata = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            upload_url = self._start_resumable_session(access_token, metadata, video)
            video_id = self._upload_bytes(access_token, upload_url, video)
            if video_id:
                return PublishResult(
                    True, self.platform, f"Subido a YouTube: https://youtu.be/{video_id}"
                )
            return PublishResult(
                False, self.platform, "Subida a YouTube sin id de video", manual=True
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("YouTube publish error: %s", exc)
            return PublishResult(
                False, self.platform, f"Error API YouTube: {exc}. Usar carpeta manual.", manual=True
            )

    def _refresh_access_token(self) -> str:
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": self.settings.youtube_client_id,
                "client_secret": self.settings.youtube_client_secret,
                "refresh_token": self.settings.youtube_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("No se obtuvo access_token de Google OAuth")
        return token

    def _start_resumable_session(self, access_token: str, metadata: dict, video: Path) -> str:
        resp = requests.post(
            UPLOAD_URL,
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
                "X-Upload-Content-Length": str(video.stat().st_size),
            },
            json=metadata,
            timeout=30,
        )
        resp.raise_for_status()
        location = resp.headers.get("Location")
        if not location:
            raise RuntimeError("YouTube no devolvió URL de subida reanudable")
        return location

    def _upload_bytes(self, access_token: str, upload_url: str, video: Path) -> str | None:
        with video.open("rb") as f:
            resp = requests.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/*",
                },
                data=f,
                timeout=600,
            )
        resp.raise_for_status()
        return resp.json().get("id")

    @staticmethod
    def _read(path: Path, default: str) -> str:
        return path.read_text(encoding="utf-8").strip() if path.exists() else default
