"""Servicio de analíticas y tendencias."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from utils.config import ensure_dir, get_settings

PLATFORMS = ["instagram", "tiktok", "facebook", "youtube", "x"]
ANALYTICS_DIR = "data/analytics"


def _analytics_path() -> Path:
    return ensure_dir(get_settings().project_root / ANALYTICS_DIR)


def _snapshot_file(platform: str) -> Path:
    return _analytics_path() / f"{platform}.json"


def _load_snapshots(platform: str) -> list[dict[str, Any]]:
    path = _snapshot_file(platform)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_snapshots(platform: str, data: list[dict[str, Any]]) -> None:
    _snapshot_file(platform).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _platform_configured(platform: str, settings) -> bool:
    checks = {
        "instagram": settings.has_meta(),
        "facebook": settings.has_meta(),
        "tiktok": bool(settings.tiktok_access_token),
        "youtube": bool(settings.youtube_refresh_token),
        "x": bool(settings.x_bearer_token or settings.x_api_key),
    }
    return checks.get(platform, False)


def _generate_demo_metrics(platform: str) -> dict[str, Any]:
    base = {
        "instagram": {"followers": 12400, "engagement_rate": 4.2},
        "tiktok": {"followers": 8900, "engagement_rate": 6.8},
        "facebook": {"followers": 5600, "engagement_rate": 2.1},
        "youtube": {"followers": 3200, "engagement_rate": 5.5},
        "x": {"followers": 4100, "engagement_rate": 3.0},
    }
    b = base.get(platform, {"followers": 1000, "engagement_rate": 3.0})
    return {
        "followers": b["followers"] + random.randint(-50, 120),
        "engagement_rate": round(b["engagement_rate"] + random.uniform(-0.3, 0.3), 2),
        "posts_this_week": random.randint(2, 7),
        "top_hashtags": ["#motivacion", "#filosofia", "#crecimientopersonal", "#mindfulness"],
    }


def ensure_daily_snapshot() -> None:
    """Registra snapshot diario para tendencias (demo o real)."""
    settings = get_settings()
    today = datetime.now().strftime("%Y-%m-%d")

    for platform in PLATFORMS:
        snapshots = _load_snapshots(platform)
        if snapshots and snapshots[-1].get("date") == today:
            continue

        if _platform_configured(platform, settings):
            metrics = _fetch_live_metrics(platform, settings)
            source = "api"
        else:
            metrics = _generate_demo_metrics(platform)
            source = "demo"

        snapshots.append(
            {
                "date": today,
                "source": source,
                "metrics": metrics,
            }
        )
        if len(snapshots) > 90:
            snapshots = snapshots[-90:]
        _save_snapshots(platform, snapshots)


def _fetch_live_metrics(platform: str, settings) -> dict[str, Any]:
    """Placeholder para integración real — devuelve demo enriquecido."""
    metrics = _generate_demo_metrics(platform)
    metrics["note"] = "Datos simulados — conectar endpoints reales de cada plataforma"
    return metrics


def get_platform_metrics() -> list[dict[str, Any]]:
    ensure_daily_snapshot()
    settings = get_settings()
    result = []

    for platform in PLATFORMS:
        snapshots = _load_snapshots(platform)
        latest = snapshots[-1] if snapshots else None
        configured = _platform_configured(platform, settings)
        metrics = latest["metrics"] if latest else _generate_demo_metrics(platform)

        result.append(
            {
                "platform": platform,
                "label": platform.capitalize() if platform != "x" else "X",
                "configured": configured,
                "source": latest.get("source", "demo") if latest else "demo",
                "metrics": metrics,
                "connect_cta": not configured,
            }
        )
    return result


def get_trends(days: int = 30) -> dict[str, Any]:
    ensure_daily_snapshot()
    settings = get_settings()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    trends: dict[str, Any] = {"platforms": {}, "hashtags": {}, "demo_mode": False}

    all_hashtags: dict[str, int] = {}
    any_demo = False

    for platform in PLATFORMS:
        snapshots = _load_snapshots(platform)
        filtered = [s for s in snapshots if s.get("date", "") >= cutoff]
        if not filtered:
            filtered = snapshots[-7:]

        followers = [s["metrics"]["followers"] for s in filtered]
        engagement = [s["metrics"]["engagement_rate"] for s in filtered]
        dates = [s["date"] for s in filtered]
        posts = [s["metrics"].get("posts_this_week", 0) for s in filtered]

        if any(s.get("source") == "demo" for s in filtered):
            any_demo = True

        for s in filtered:
            for tag in s["metrics"].get("top_hashtags", []):
                all_hashtags[tag] = all_hashtags.get(tag, 0) + 1

        trends["platforms"][platform] = {
            "dates": dates,
            "followers": followers,
            "engagement_rate": engagement,
            "posts_per_week": posts,
            "configured": _platform_configured(platform, settings),
        }

    trends["hashtags"] = sorted(all_hashtags.items(), key=lambda x: x[1], reverse=True)[:10]
    trends["demo_mode"] = any_demo or not any(
        _platform_configured(p, settings) for p in PLATFORMS
    )
    return trends
