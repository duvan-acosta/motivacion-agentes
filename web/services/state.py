"""Estado global en memoria para el panel web."""

from __future__ import annotations

import os
from datetime import datetime
from threading import Lock
from typing import Any

from utils.config import get_settings

_lock = Lock()
_activity: list[dict[str, Any]] = []
_agent_status: dict[str, str] = {
    "director": "idle",
    "content_creator": "idle",
    "visual_designer": "idle",
    "video_producer": "idle",
    "publisher": "idle",
}
_last_run: dict[str, Any] | None = None
_generation_running = False
_publish_running: dict[str, bool] = {}
_demo_mode_override: bool | None = None


def _now() -> str:
    return datetime.now().isoformat()


def add_activity(message: str, kind: str = "info", meta: dict[str, Any] | None = None) -> None:
    with _lock:
        entry = {"timestamp": _now(), "message": message, "kind": kind}
        if meta:
            entry["meta"] = meta
        _activity.insert(0, entry)
        del _activity[50:]


def get_activity(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        return list(_activity[:limit])


def set_agent_status(agent_id: str, status: str) -> None:
    with _lock:
        if agent_id in _agent_status:
            _agent_status[agent_id] = status


def set_all_agents(status: str) -> None:
    with _lock:
        for key in _agent_status:
            _agent_status[key] = status


def get_agent_status() -> dict[str, str]:
    with _lock:
        return dict(_agent_status)


def set_last_run(data: dict[str, Any]) -> None:
    global _last_run
    with _lock:
        _last_run = data


def get_last_run() -> dict[str, Any] | None:
    with _lock:
        return dict(_last_run) if _last_run else None


def is_generation_running() -> bool:
    with _lock:
        return _generation_running


def set_generation_running(running: bool) -> None:
    global _generation_running
    with _lock:
        _generation_running = running


def is_publish_running(package_id: str) -> bool:
    with _lock:
        return _publish_running.get(package_id, False)


def set_publish_running(package_id: str, running: bool) -> None:
    with _lock:
        if running:
            _publish_running[package_id] = True
        else:
            _publish_running.pop(package_id, None)


def get_demo_mode() -> bool:
    if _demo_mode_override is not None:
        return _demo_mode_override
    return get_settings().demo_mode


def set_demo_mode(enabled: bool) -> None:
    global _demo_mode_override
    with _lock:
        _demo_mode_override = enabled
        os.environ["DEMO_MODE"] = "true" if enabled else "false"
        get_settings.cache_clear()
    add_activity(
        f"Modo {'demo' if enabled else 'producción'} activado",
        kind="config",
    )


def apply_demo_for_job(demo: bool | None) -> None:
    """Aplica modo demo temporal para una tarea en background."""
    use_demo = demo if demo is not None else get_demo_mode()
    os.environ["DEMO_MODE"] = "true" if use_demo else "false"
    get_settings.cache_clear()
