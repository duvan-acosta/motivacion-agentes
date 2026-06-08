"""Tests de transiciones de estado en BasePublisherAdapter."""

from __future__ import annotations

import json
from pathlib import Path

from publishing.base_adapter import BasePublisherAdapter, PublishResult


class _DummyAdapter(BasePublisherAdapter):
    platform = "dummy"

    def can_publish(self) -> bool:
        return True

    def publish(self, package_path: Path) -> PublishResult:  # pragma: no cover - no usado
        return PublishResult(True, self.platform, "ok")


def _read_status(pkg: Path) -> dict:
    return json.loads((pkg / "status.json").read_text(encoding="utf-8"))


def test_success_marks_published(tmp_path):
    adapter = _DummyAdapter()
    adapter.update_status(tmp_path, "instagram", PublishResult(True, "instagram", "ok"))
    status = _read_status(tmp_path)
    assert status["platforms"]["instagram"] == "published"
    assert status["status"] == "published"


def test_manual_marks_manual(tmp_path):
    adapter = _DummyAdapter()
    adapter.update_status(tmp_path, "tiktok", PublishResult(False, "tiktok", "x", manual=True))
    status = _read_status(tmp_path)
    assert status["platforms"]["tiktok"] == "manual"
    assert status["status"] == "manual"


def test_mixed_results_overall_manual(tmp_path):
    adapter = _DummyAdapter()
    adapter.update_status(tmp_path, "instagram", PublishResult(True, "instagram", "ok"))
    adapter.update_status(tmp_path, "tiktok", PublishResult(False, "tiktok", "x", manual=True))
    status = _read_status(tmp_path)
    assert status["status"] == "manual"


def test_publish_result_to_dict():
    d = PublishResult(False, "x", "msg", manual=True).to_dict()
    assert d["success"] is False
    assert d["manual"] is True
    assert d["platform"] == "x"
    assert "timestamp" in d
