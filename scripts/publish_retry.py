#!/usr/bin/env python3
"""Reintenta publicaciones pendientes o fallidas."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from graph.workflow import MotivacionWorkflow
from utils.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def find_pending_packages(queue_dir: Path) -> list[Path]:
    pending = []
    for date_dir in sorted(queue_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        for pkg in sorted(date_dir.iterdir()):
            if not pkg.is_dir():
                continue
            status_file = pkg / "status.json"
            if not status_file.exists():
                pending.append(pkg)
                continue
            status = json.loads(status_file.read_text(encoding="utf-8"))
            if status.get("status") in ("pending", "manual", "failed"):
                pending.append(pkg)
    return pending


def main() -> int:
    settings = get_settings()
    queue_dir = settings.queue_path
    if not queue_dir.exists():
        logger.error("No existe publication_queue en %s", queue_dir)
        return 1

    packages = find_pending_packages(queue_dir)
    if not packages:
        logger.info("No hay paquetes pendientes de publicación")
        return 0

    workflow = MotivacionWorkflow()
    for pkg in packages:
        logger.info("Reintentando publicación: %s", pkg)
        results = workflow.publish_package(str(pkg))
        for r in results:
            logger.info("  %s: success=%s manual=%s — %s", r["platform"], r["success"], r.get("manual"), r["message"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
