"""Router de configuración (.env)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from web.services import config_service

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    values: dict[str, str]


@router.get("")
def get_config():
    return config_service.get_config_form()


@router.post("")
def update_config(body: ConfigUpdateRequest):
    return config_service.update_config(body.values)
