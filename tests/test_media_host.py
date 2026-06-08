"""Tests del hosting público de media."""

from __future__ import annotations

from pathlib import Path


def test_none_provider_returns_no_url(make_settings):
    make_settings(MEDIA_HOST_PROVIDER="none")
    from publishing.media_host import NoneMediaHost, build_media_host

    host = build_media_host()
    assert isinstance(host, NoneMediaHost)
    assert host.available() is False
    assert host.upload(Path("whatever.jpg")) is None


def test_base_url_provider_builds_relative_url(make_settings):
    settings = make_settings(
        MEDIA_HOST_PROVIDER="base_url",
        MEDIA_PUBLIC_BASE_URL="https://cdn.test/files",
    )
    from publishing.media_host import BaseUrlMediaHost, build_media_host

    host = build_media_host()
    assert isinstance(host, BaseUrlMediaHost)
    assert host.available() is True

    # Crea un archivo dentro de publication_queue.
    target = settings.queue_path / "2026-06-08" / "msg_x" / "instagram" / "feed.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"fake")

    url = host.upload(target)
    assert url == "https://cdn.test/files/2026-06-08/msg_x/instagram/feed.jpg"


def test_base_url_unavailable_without_url(make_settings):
    make_settings(MEDIA_HOST_PROVIDER="base_url", MEDIA_PUBLIC_BASE_URL="")
    from publishing.media_host import build_media_host

    host = build_media_host()
    assert host.available() is False
    assert host.upload(Path("x.jpg")) is None
