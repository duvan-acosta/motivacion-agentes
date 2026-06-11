"""Tests: sin credenciales, los adaptadores caen a publicación manual."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_package(base: Path) -> Path:
    """Crea un paquete con los archivos mínimos que esperan los adaptadores."""
    for sub, files in {
        "instagram": ["feed.jpg", "caption.txt", "hashtags.txt"],
        "tiktok": ["video.mp4", "caption.txt"],
        "youtube": ["short.mp4", "title.txt", "description.txt", "tags.txt"],
        "twitter": ["image.jpg", "tweet.txt"],
        "facebook": ["post.jpg", "caption.txt"],
    }.items():
        d = base / sub
        d.mkdir(parents=True, exist_ok=True)
        for f in files:
            (d / f).write_bytes(b"x")
    return base


def _status(pkg: Path) -> dict:
    return json.loads((pkg / "status.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "module,cls,platform",
    [
        ("publishing.adapters.meta_instagram", "MetaInstagramAdapter", "instagram"),
        ("publishing.adapters.tiktok", "TikTokAdapter", "tiktok"),
        ("publishing.adapters.youtube", "YouTubeAdapter", "youtube"),
        ("publishing.adapters.twitter", "TwitterAdapter", "twitter"),
        ("publishing.adapters.pinterest", "PinterestAdapter", "pinterest"),
    ],
)
def test_adapter_manual_fallback_without_credentials(make_settings, tmp_path, module, cls, platform):
    make_settings()  # sin credenciales
    pkg = _make_package(tmp_path / "pkg")

    import importlib

    adapter = getattr(importlib.import_module(module), cls)()
    result = adapter.publish(pkg)

    assert result.success is False
    assert result.manual is True
    assert _status(pkg)["platforms"][platform] == "manual"
