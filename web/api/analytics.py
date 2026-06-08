"""Router de analíticas."""

from __future__ import annotations

from fastapi import APIRouter, Query

from web.services.analytics_service import get_platform_metrics, get_trends

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/platforms")
def platform_metrics():
    return {"platforms": get_platform_metrics()}


@router.get("/trends")
def analytics_trends(days: int = Query(default=30, ge=7, le=90)):
    return get_trends(days=days)
