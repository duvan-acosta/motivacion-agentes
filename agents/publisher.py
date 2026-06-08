"""PublisherAgent — empaqueta contenido por plataforma."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from utils.config import ensure_dir, get_settings, load_yaml
from utils.demo_mode import demo_tweet, demo_youtube_meta

logger = logging.getLogger(__name__)


class PublisherAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.platforms = load_yaml("config/platforms.yaml")

    def _validate_image(self, path: Path, width: int, height: int) -> bool:
        if not path.exists():
            return False
        try:
            with Image.open(path) as img:
                return img.size == (width, height)
        except Exception:
            return False

    def _validate_video_exists(self, path: Path) -> bool:
        return path.exists() and path.stat().st_size > 0

    def package(
        self,
        content_id: str,
        theme: str,
        message: str,
        caption: str,
        hashtags: list[str],
        script: str,
        images: dict[str, str],
        video_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        base = ensure_dir(self.settings.queue_path / date_str / content_id)

        source_dir = ensure_dir(base / "source")
        (source_dir / "message.txt").write_text(message, encoding="utf-8")
        (source_dir / "script.txt").write_text(script, encoding="utf-8")
        meta = {
            "content_id": content_id,
            "theme": theme,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }
        (source_dir / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        hashtag_text = " ".join(hashtags)
        ig_dir = ensure_dir(base / "instagram")
        self._copy_if_exists(images.get("instagram_feed"), ig_dir / "feed.jpg")
        self._copy_if_exists(video_path, ig_dir / "reel.mp4")
        (ig_dir / "caption.txt").write_text(caption, encoding="utf-8")
        (ig_dir / "hashtags.txt").write_text(hashtag_text, encoding="utf-8")

        tt_dir = ensure_dir(base / "tiktok")
        self._copy_if_exists(video_path, tt_dir / "video.mp4")
        tt_caption = f"{message}\n\n{hashtag_text}"[:2200]
        (tt_dir / "caption.txt").write_text(tt_caption, encoding="utf-8")

        fb_dir = ensure_dir(base / "facebook")
        self._copy_if_exists(images.get("facebook_post"), fb_dir / "post.jpg")
        self._copy_if_exists(video_path, fb_dir / "reel.mp4")
        (fb_dir / "caption.txt").write_text(caption, encoding="utf-8")

        yt_dir = ensure_dir(base / "youtube")
        self._copy_if_exists(video_path, yt_dir / "short.mp4")
        self._copy_if_exists(images.get("youtube_thumb"), yt_dir / "thumbnail.jpg")
        yt = demo_youtube_meta(message, theme)
        (yt_dir / "title.txt").write_text(yt["title"], encoding="utf-8")
        (yt_dir / "description.txt").write_text(yt["description"], encoding="utf-8")
        (yt_dir / "tags.txt").write_text(yt["tags"], encoding="utf-8")

        tw_dir = ensure_dir(base / "twitter")
        self._copy_if_exists(images.get("twitter_image"), tw_dir / "image.jpg")
        (tw_dir / "tweet.txt").write_text(demo_tweet(message, theme), encoding="utf-8")

        manifest = self._build_manifest(base)
        (base / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        ready = self._validate_package(base)
        status = {
            "status": "ready" if ready else "pending",
            "validated_at": datetime.now().isoformat(),
            "platforms": {p: "ready" if ready else "pending" for p in manifest["platforms"]},
        }
        (base / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info("Paquete creado en %s (ready=%s)", base, ready)
        return base

    def _copy_if_exists(self, src: str | None, dest: Path) -> None:
        if src and Path(src).exists():
            shutil.copy2(src, dest)

    def _build_manifest(self, base: Path) -> dict[str, Any]:
        specs = load_yaml("config/platforms.yaml")
        files_map = {
            "instagram": ["feed.jpg", "reel.mp4", "caption.txt", "hashtags.txt"],
            "tiktok": ["video.mp4", "caption.txt"],
            "facebook": ["post.jpg", "reel.mp4", "caption.txt"],
            "youtube": ["short.mp4", "title.txt", "description.txt", "tags.txt"],
            "twitter": ["image.jpg", "tweet.txt"],
        }
        platforms = {}
        for platform, files in files_map.items():
            platform_files = []
            for fname in files:
                fpath = base / platform / fname
                platform_files.append(
                    {
                        "file": fname,
                        "exists": fpath.exists(),
                        "size_bytes": fpath.stat().st_size if fpath.exists() else 0,
                    }
                )
            platforms[platform] = {
                "files": platform_files,
                "specs": specs.get("platforms", {}).get(platform, {}),
            }
        return {"content_path": str(base), "platforms": platforms, "generated_at": datetime.now().isoformat()}

    def _validate_package(self, base: Path) -> bool:
        checks = [
            (base / "instagram" / "feed.jpg", 1080, 1080),
            (base / "twitter" / "image.jpg", 1200, 675),
            (base / "instagram" / "reel.mp4", None, None),
        ]
        for path, w, h in checks:
            if w and h:
                if not self._validate_image(path, w, h):
                    return False
            elif not self._validate_video_exists(path):
                return False
        return True
