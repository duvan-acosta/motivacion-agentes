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
    # El caption empieza con el texto original; el sistema puede anexar un CTA
    # del producto activo después (probado en test_package_injects_cta_per_platform).
    assert (pkg / "instagram" / "caption.txt").read_text(encoding="utf-8").startswith(
        "Caption de prueba"
    )
    assert (pkg / "instagram" / "hashtags.txt").read_text(encoding="utf-8") == "#test #demo"

    status = json.loads((pkg / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "ready"


def test_package_injects_cta_per_platform(make_settings, tmp_path):
    make_settings()
    from agents.publisher import PublisherAgent

    agent = PublisherAgent()
    pkg = agent.package(
        content_id="msg_cta_test",
        theme="calma",
        message="Mensaje",
        caption="Caption base",
        hashtags=["#test"],
        script="frase",
        images={},
        video_path="",
    )

    ig_caption = (pkg / "instagram" / "caption.txt").read_text(encoding="utf-8")
    yt_desc = (pkg / "youtube" / "description.txt").read_text(encoding="utf-8")
    tweet = (pkg / "twitter" / "tweet.txt").read_text(encoding="utf-8")

    # Instagram: CTA con "link en bio", sin URL clicable.
    assert "link en bio" in ig_caption.lower()
    assert "http" not in ig_caption
    # YouTube y X sí incluyen la URL con UTM.
    assert "utm_source=yt" in yt_desc
    assert "utm_source=x" in tweet

    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("promoted_product", {}).get("id") == "wallpapers_pack"
