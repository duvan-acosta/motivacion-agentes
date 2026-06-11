"""Resolución del access token de Pinterest (API v5).

Dos modos, para cubrir desde el arranque rápido hasta la automatización total:

- **Estático**: ``PINTEREST_ACCESS_TOKEN``. Lo más rápido para empezar (el portal
  de desarrollador genera un token de Trial). Caduca en semanas.
- **Refresh**: ``PINTEREST_REFRESH_TOKEN`` + ``PINTEREST_APP_ID`` +
  ``PINTEREST_APP_SECRET``. Obtiene un access token fresco en cada uso, así la
  automatización no se rompe cuando el token estático caduca.

Si hay credenciales de refresh se prefieren (token siempre vigente); si el
refresh falla, se intenta el token estático como respaldo.
"""

from __future__ import annotations

import base64
import logging

import requests

from utils.config import Settings

logger = logging.getLogger(__name__)

OAUTH_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"


def _refresh(settings: Settings) -> str | None:
    """Canjea el refresh token por un access token nuevo."""
    try:
        basic = base64.b64encode(
            f"{settings.pinterest_app_id}:{settings.pinterest_app_secret}".encode()
        ).decode("ascii")
        resp = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": settings.pinterest_refresh_token,
            },
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as exc:  # noqa: BLE001
        logger.error("Refresh del token de Pinterest falló: %s", exc)
        return None


def resolve_access_token(settings: Settings) -> str | None:
    """Devuelve un access token válido, o ``None`` si no hay credenciales."""
    has_refresh = bool(
        settings.pinterest_refresh_token
        and settings.pinterest_app_id
        and settings.pinterest_app_secret
    )
    if has_refresh:
        token = _refresh(settings)
        if token:
            return token
        logger.warning("Refresh falló; usando PINTEREST_ACCESS_TOKEN como respaldo")
    return settings.pinterest_access_token or None
