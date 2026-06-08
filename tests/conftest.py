"""Fixtures compartidas para la suite de tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Asegura que el paquete raíz del proyecto esté importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Variables de entorno que deben quedar vacías para tests deterministas.
_CREDENTIAL_ENV = [
    "OPENAI_API_KEY", "PEXELS_API_KEY", "ELEVENLABS_API_KEY",
    "META_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID", "META_FACEBOOK_PAGE_ID",
    "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN",
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
    "MEDIA_HOST_PROVIDER", "MEDIA_PUBLIC_BASE_URL", "S3_BUCKET",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "CLOUDINARY_URL",
]


def _clear_settings_cache() -> None:
    from utils.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def make_settings(monkeypatch, tmp_path):
    """Devuelve un constructor de Settings con entorno controlado.

    Limpia las credenciales, apunta publication_queue/chroma a ``tmp_path`` y
    aplica los overrides pasados como kwargs (claves = nombres de variables env).
    """

    def _factory(**env: str):
        for key in _CREDENTIAL_ENV:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("PUBLICATION_QUEUE_DIR", str(tmp_path / "queue"))
        monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
        for key, value in env.items():
            monkeypatch.setenv(key, str(value))
        _clear_settings_cache()
        from utils.config import get_settings

        return get_settings()

    yield _factory
    _clear_settings_cache()
