"""Router del dashboard."""

from __future__ import annotations

from fastapi import APIRouter

from web.services import content_service, state
from web.services.agent_service import list_agents
from web.services.analytics_service import ensure_daily_snapshot

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary():
    ensure_daily_snapshot()
    counts = content_service.count_by_status()
    agents = list_agents()
    running = sum(1 for a in agents if a.get("status") == "running")
    errors = sum(1 for a in agents if a.get("status") == "error")

    agent_status = {a["id"]: a.get("status", "idle") for a in agents}
    return {
        "counts": counts,
        "agents": {
            "total": len(agents),
            "running": running,
            "idle": len(agents) - running - errors,
            "error": errors,
            "status": agent_status,
        },
        "generation_running": state.is_generation_running(),
        "demo_mode": state.get_demo_mode(),
        "recent_activity": state.get_activity(15),
        "last_run": state.get_last_run(),
    }
