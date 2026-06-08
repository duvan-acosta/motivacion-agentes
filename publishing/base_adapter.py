"""Interfaz base para adaptadores de publicación."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PublishResult:
    def __init__(self, success: bool, platform: str, message: str, manual: bool = False) -> None:
        self.success = success
        self.platform = platform
        self.message = message
        self.manual = manual

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "message": self.message,
            "manual": self.manual,
            "timestamp": datetime.now().isoformat(),
        }


class BasePublisherAdapter(ABC):
    platform: str = "base"

    @abstractmethod
    def can_publish(self) -> bool:
        ...

    @abstractmethod
    def publish(self, package_path: Path) -> PublishResult:
        ...

    def update_status(self, package_path: Path, platform: str, result: PublishResult) -> None:
        status_file = package_path / "status.json"
        status: dict[str, Any] = {"status": "pending", "platforms": {}}
        if status_file.exists():
            status = json.loads(status_file.read_text(encoding="utf-8"))

        if result.success:
            status["platforms"][platform] = "published"
        elif result.manual:
            status["platforms"][platform] = "manual"
        else:
            status["platforms"][platform] = "failed"

        all_published = all(v == "published" for v in status["platforms"].values())
        any_manual = any(v == "manual" for v in status["platforms"].values())
        if all_published:
            status["status"] = "published"
        elif any_manual:
            status["status"] = "manual"
        else:
            status["status"] = "pending"

        status["last_publish_attempt"] = datetime.now().isoformat()
        status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
