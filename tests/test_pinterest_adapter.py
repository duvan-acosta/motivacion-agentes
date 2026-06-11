"""Tests del PinterestAdapter: payload base64 + link con UTM."""

from __future__ import annotations

import json
from pathlib import Path


def _make_package(base: Path) -> Path:
    ig = base / "instagram"
    ig.mkdir(parents=True, exist_ok=True)
    (ig / "feed.jpg").write_bytes(b"\xff\xd8\xff\xe0fakejpeg")
    (ig / "caption.txt").write_text("Hoy puedes empezar de nuevo.", encoding="utf-8")
    (ig / "hashtags.txt").write_text("#calma #motivacion", encoding="utf-8")
    src = base / "source"
    src.mkdir(parents=True, exist_ok=True)
    (src / "message.txt").write_text("Respira. Vas a estar bien.", encoding="utf-8")
    return base


class _FakeResp:
    status_code = 201

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": "pin_123"}


def test_pinterest_publishes_with_base64_and_utm_link(make_settings, tmp_path, monkeypatch):
    make_settings(PINTEREST_ACCESS_TOKEN="tok", PINTEREST_BOARD_ID="board_1")
    pkg = _make_package(tmp_path / "msg_test_calma_001")

    captured: dict = {}

    def _fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _FakeResp()

    from publishing.adapters import pinterest

    monkeypatch.setattr(pinterest.requests, "post", _fake_post)

    adapter = pinterest.PinterestAdapter()
    result = adapter.publish(pkg)

    assert result.success is True
    payload = captured["json"]
    # La imagen va embebida en base64 (sin media host).
    assert payload["media_source"]["source_type"] == "image_base64"
    assert payload["media_source"]["data"]
    assert payload["board_id"] == "board_1"
    assert captured["headers"]["Authorization"] == "Bearer tok"
    # El link de destino lleva el UTM de Pinterest y el id del contenido.
    assert "utm_source=pin" in payload["link"]
    assert "utm_content=msg_test_calma_001" in payload["link"]
    # status.json refleja la publicación.
    status = json.loads((pkg / "status.json").read_text(encoding="utf-8"))
    assert status["platforms"]["pinterest"] == "published"
