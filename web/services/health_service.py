"""Servicio de salud de servicios externos."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from typing import Any

from utils.config import get_settings


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}…{value[-4:]}"


def _key_status(configured: bool, label: str, masked: str = "") -> dict[str, Any]:
    return {
        "configured": configured,
        "label": label,
        "masked_key": masked if configured else None,
        "status": "ok" if configured else "missing",
    }


def check_openai(settings) -> dict[str, Any]:
    ok = settings.has_openai()
    return {
        "id": "openai",
        "name": "OpenAI",
        "description": "GPT-4o, embeddings y TTS",
        **_key_status(ok, "OPENAI_API_KEY", mask_key(settings.openai_api_key)),
    }


def check_pexels(settings) -> dict[str, Any]:
    ok = settings.has_pexels()
    return {
        "id": "pexels",
        "name": "Pexels",
        "description": "Fondos foto y video",
        **_key_status(ok, "PEXELS_API_KEY", mask_key(settings.pexels_api_key)),
    }


def check_elevenlabs(settings) -> dict[str, Any]:
    ok = bool(settings.elevenlabs_api_key)
    return {
        "id": "elevenlabs",
        "name": "ElevenLabs",
        "description": "Text-to-speech alternativo",
        **_key_status(ok, "ELEVENLABS_API_KEY", mask_key(settings.elevenlabs_api_key)),
    }


def check_meta(settings) -> dict[str, Any]:
    ok = settings.has_meta()
    masked = mask_key(settings.meta_access_token) if ok else ""
    return {
        "id": "meta",
        "name": "Meta (Instagram/Facebook)",
        "description": "Graph API para publicación",
        "configured": ok,
        "masked_key": masked or None,
        "status": "ok" if ok else "missing",
        "details": {
            "access_token": ok,
            "instagram_account_id": bool(settings.meta_instagram_account_id),
        },
    }


def check_tiktok(settings) -> dict[str, Any]:
    ok = bool(settings.tiktok_access_token or settings.tiktok_client_key)
    return {
        "id": "tiktok",
        "name": "TikTok",
        "description": "Content Posting API",
        **_key_status(ok, "TIKTOK_ACCESS_TOKEN", mask_key(settings.tiktok_access_token)),
    }


def check_youtube(settings) -> dict[str, Any]:
    ok = bool(settings.youtube_refresh_token or settings.youtube_client_id)
    return {
        "id": "youtube",
        "name": "YouTube",
        "description": "Data API v3",
        **_key_status(ok, "YOUTUBE_REFRESH_TOKEN", mask_key(settings.youtube_refresh_token)),
    }


def check_x(settings) -> dict[str, Any]:
    ok = bool(settings.x_bearer_token or settings.x_api_key)
    masked = mask_key(settings.x_bearer_token or settings.x_api_key)
    return {
        "id": "x",
        "name": "X (Twitter)",
        "description": "API v2",
        **_key_status(ok, "X_BEARER_TOKEN", masked),
    }


def get_scheduler_status() -> dict[str, Any]:
    settings = get_settings()
    now = datetime.now()
    next_run = now.replace(
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        second=0,
        microsecond=0,
    )
    if next_run <= now:
        next_run += timedelta(days=1)

    running = _detect_docker_service("scheduler")
    return {
        "status": "running" if running else "stopped",
        "schedule": f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d}",
        "timezone": settings.timezone,
        "next_run": next_run.isoformat(),
        "detected_in_docker": running,
    }


def _detect_docker_service(name: str) -> bool:
    if not os.path.exists("/.dockerenv") and not os.environ.get("DOCKER_CONTAINER"):
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--services", "--filter", f"status=running"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(get_settings().project_root),
            )
            if result.returncode == 0:
                services = result.stdout.strip().splitlines()
                return name in services
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return False
    return os.environ.get("SCHEDULER_RUNNING", "").lower() == "true"


def get_docker_services() -> list[dict[str, Any]]:
    services = [
        {"name": "motivacion-agentes", "role": "CLI principal"},
        {"name": "generate-demo", "role": "Generación demo"},
        {"name": "scheduler", "role": "Generación diaria"},
        {"name": "web", "role": "Panel de administración"},
    ]
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(get_settings().project_root),
        )
        if result.returncode == 0 and result.stdout.strip():
            import json

            lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
            running = set()
            for line in lines:
                try:
                    item = json.loads(line)
                    running.add(item.get("Service", item.get("Name", "")))
                except json.JSONDecodeError:
                    continue
            for svc in services:
                svc["status"] = "running" if svc["name"] in running else "unknown"
            return services
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    for svc in services:
        svc["status"] = "unknown"
    if os.path.exists("/.dockerenv"):
        for svc in services:
            if svc["name"] == "web":
                svc["status"] = "running"
    return services


def get_services_health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "services": [
            check_openai(settings),
            check_pexels(settings),
            check_elevenlabs(settings),
            check_meta(settings),
            check_tiktok(settings),
            check_youtube(settings),
            check_x(settings),
        ],
        "scheduler": get_scheduler_status(),
        "docker": get_docker_services(),
        "demo_mode": settings.demo_mode,
        "mock_mode": settings.use_mock(),
    }
