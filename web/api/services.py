"""Router de servicios externos."""

from __future__ import annotations

from fastapi import APIRouter

from web.services.health_service import get_services_health

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/health")
def services_health():
    return get_services_health()
