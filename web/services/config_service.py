"""Lectura y escritura segura de variables de entorno (.env)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from utils.config import PROJECT_ROOT, get_settings
from web.services.health_service import mask_key

ENV_FILE = PROJECT_ROOT / ".env"

CONFIG_GROUPS: list[dict[str, Any]] = [
    {
        "id": "content",
        "label": "Generación de contenido",
        "fields": [
            {"key": "OPENAI_API_KEY", "label": "OpenAI / LLM API Key", "type": "secret", "required": True},
            {"key": "OPENAI_MODEL", "label": "Modelo LLM (gpt-4o-mini, deepseek-chat, ...)", "type": "text"},
            {
                "key": "OPENAI_BASE_URL",
                "label": "LLM Base URL (vacío = OpenAI; DeepSeek: https://api.deepseek.com)",
                "type": "text",
            },
            {"key": "PEXELS_API_KEY", "label": "Pexels API Key", "type": "secret"},
            {"key": "ELEVENLABS_API_KEY", "label": "ElevenLabs API Key", "type": "secret"},
            {"key": "ELEVENLABS_VOICE_ID", "label": "ElevenLabs Voice ID", "type": "text"},
            {"key": "TTS_PROVIDER", "label": "Proveedor TTS", "type": "select", "options": ["openai", "elevenlabs"]},
        ],
    },
    {
        "id": "meta",
        "label": "Instagram / Facebook (Meta)",
        "fields": [
            {"key": "META_ACCESS_TOKEN", "label": "Meta Access Token", "type": "secret"},
            {"key": "META_INSTAGRAM_ACCOUNT_ID", "label": "Instagram Account ID", "type": "text"},
            {"key": "META_FACEBOOK_PAGE_ID", "label": "Facebook Page ID", "type": "text"},
        ],
    },
    {
        "id": "tiktok",
        "label": "TikTok",
        "fields": [
            {"key": "TIKTOK_CLIENT_KEY", "label": "Client Key", "type": "secret"},
            {"key": "TIKTOK_CLIENT_SECRET", "label": "Client Secret", "type": "secret"},
            {"key": "TIKTOK_ACCESS_TOKEN", "label": "Access Token", "type": "secret"},
        ],
    },
    {
        "id": "youtube",
        "label": "YouTube",
        "fields": [
            {"key": "YOUTUBE_CLIENT_ID", "label": "Client ID", "type": "text"},
            {"key": "YOUTUBE_CLIENT_SECRET", "label": "Client Secret", "type": "secret"},
            {"key": "YOUTUBE_REFRESH_TOKEN", "label": "Refresh Token", "type": "secret"},
        ],
    },
    {
        "id": "x",
        "label": "X (Twitter)",
        "fields": [
            {"key": "X_API_KEY", "label": "API Key", "type": "secret"},
            {"key": "X_API_SECRET", "label": "API Secret", "type": "secret"},
            {"key": "X_ACCESS_TOKEN", "label": "Access Token", "type": "secret"},
            {"key": "X_ACCESS_TOKEN_SECRET", "label": "Access Token Secret", "type": "secret"},
            {"key": "X_BEARER_TOKEN", "label": "Bearer Token", "type": "secret"},
        ],
    },
    {
        "id": "scheduler",
        "label": "Programación",
        "fields": [
            {"key": "SCHEDULE_HOUR", "label": "Hora de generación (0-23)", "type": "number"},
            {"key": "SCHEDULE_MINUTE", "label": "Minuto (0-59)", "type": "number"},
            {
                "key": "TIMEZONE",
                "label": "Zona horaria",
                "type": "select",
                "options": [
                    "America/Bogota",
                    "America/Mexico_City",
                    "America/Lima",
                    "America/Santiago",
                    "America/Argentina/Buenos_Aires",
                    "America/Caracas",
                    "America/La_Paz",
                    "America/Guayaquil",
                    "America/Asuncion",
                    "America/Montevideo",
                    "America/Costa_Rica",
                    "America/Panama",
                    "America/Guatemala",
                    "America/Santo_Domingo",
                    "America/Havana",
                    "America/Sao_Paulo",
                    "America/New_York",
                    "America/Los_Angeles",
                    "Europe/Madrid",
                    "Europe/London",
                    "UTC",
                ],
            },
            {"key": "DEMO_MODE", "label": "Modo demo", "type": "select", "options": ["true", "false"]},
            {"key": "MOCK_MODE", "label": "Modo mock", "type": "select", "options": ["true", "false"]},
        ],
    },
]

ENV_KEY_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _read_env_map() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    result: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ENV_KEY_PATTERN.match(stripped)
        if match:
            key, value = match.group(1), match.group(2)
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            result[key] = value
    return result


def _write_env_map(updates: dict[str, str]) -> None:
    lines: list[str] = []
    seen: set[str] = set()

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            match = ENV_KEY_PATTERN.match(stripped) if stripped and not stripped.startswith("#") else None
            if match:
                key = match.group(1)
                if key in updates:
                    value = updates[key]
                    lines.append(f"{key}={value}")
                    seen.add(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)
    else:
        lines.append("# Configuración generada por el panel web")
        lines.append("")

    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    get_settings.cache_clear()
    os.environ.update(updates)


def get_config_form() -> dict[str, Any]:
    env = _read_env_map()
    groups = []
    for group in CONFIG_GROUPS:
        fields = []
        for field in group["fields"]:
            key = field["key"]
            value = env.get(key, "")
            fields.append(
                {
                    **field,
                    "value": value if field["type"] != "secret" else "",
                    "masked": mask_key(value) if value and field["type"] == "secret" else "",
                    "configured": bool(value),
                }
            )
        groups.append({**group, "fields": fields})
    return {"groups": groups, "env_path": str(ENV_FILE)}


def update_config(updates: dict[str, str]) -> dict[str, Any]:
    allowed = {f["key"] for g in CONFIG_GROUPS for f in g["fields"]}
    filtered: dict[str, str] = {}
    for key, value in updates.items():
        if key not in allowed:
            continue
        if value is None:
            continue
        value = str(value).strip()
        if value == "" or value == "••••••••" or "…" in value:
            continue
        filtered[key] = value

    if not filtered:
        return {"ok": False, "message": "No hay cambios para guardar", "updated": []}

    _write_env_map(filtered)
    return {"ok": True, "message": f"Configuración guardada ({len(filtered)} variables)", "updated": list(filtered.keys())}
