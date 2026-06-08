"""Test del empaquetado por plataforma (PublisherAgent)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _img(path: Path, size: tuple[int, int]) -> Path:
    Image.new("RGB", size, (20, 20, 30)).save(path, "JPEG")
    return path


def test_package_creates_full_structure(make_settings, tmp_path):
    make_settings()
    from agents.publisher import PublisherAgent

    media = tmp_path / "media"
    media.mkdir()
    images = {
        "instagram_feed": str(_img(media / "feed.jpg", (1080, 1080))),
        "facebook_post": str(_img(media / "fb.jpg", (1080, 1080))),
        "twitter_image": str(_img(media / "tw.jpg", (1200, 675))),
        "youtube_thumb": str(_img(media / "yt.jpg", (1280, 720))),
    }
    video = media / "reel.mp4"
    video.write_bytes(b"\x00" * 2048)

    agent = PublisherAgent()
    pkg = agent.package(
        content_id="msg_test_123",
        theme="resiliencia",
        message="Mensaje de prueba",
        caption="Caption de prueba",
        hashtags=["#test", "#demo"],
        script="Linea 1\nLinea 2",
        images=images,
        video_path=str(video),
    )

    assert pkg.exists()
    assert (pkg / "manifest.json").exists()
    assert (pkg / "status.json").exists()
    assert (pkg / "instagram" / "feed.jpg").exists()
    assert (pkg / "instagram" / "caption.txt").read_text(encoding="utf-8") == "Caption de prueba"
    assert (pkg / "instagram" / "hashtags.txt").read_text(encoding="utf-8") == "#test #demo"

    status = json.loads((pkg / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "ready"
