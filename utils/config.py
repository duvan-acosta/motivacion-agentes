"""Configuración centralizada desde .env y YAML."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    mock_mode: bool = Field(default=True, alias="MOCK_MODE")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_tts_model: str = Field(default="tts-1", alias="OPENAI_TTS_MODEL")
    openai_tts_voice: str = Field(default="nova", alias="OPENAI_TTS_VOICE")

    pexels_api_key: str = Field(default="", alias="PEXELS_API_KEY")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(default="", alias="ELEVENLABS_VOICE_ID")
    tts_provider: str = Field(default="openai", alias="TTS_PROVIDER")

    meta_access_token: str = Field(default="", alias="META_ACCESS_TOKEN")
    meta_instagram_account_id: str = Field(default="", alias="META_INSTAGRAM_ACCOUNT_ID")
    meta_facebook_page_id: str = Field(default="", alias="META_FACEBOOK_PAGE_ID")

    tiktok_client_key: str = Field(default="", alias="TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str = Field(default="", alias="TIKTOK_CLIENT_SECRET")
    tiktok_access_token: str = Field(default="", alias="TIKTOK_ACCESS_TOKEN")

    youtube_client_id: str = Field(default="", alias="YOUTUBE_CLIENT_ID")
    youtube_client_secret: str = Field(default="", alias="YOUTUBE_CLIENT_SECRET")
    youtube_refresh_token: str = Field(default="", alias="YOUTUBE_REFRESH_TOKEN")

    x_api_key: str = Field(default="", alias="X_API_KEY")
    x_api_secret: str = Field(default="", alias="X_API_SECRET")
    x_access_token: str = Field(default="", alias="X_ACCESS_TOKEN")
    x_access_token_secret: str = Field(default="", alias="X_ACCESS_TOKEN_SECRET")
    x_bearer_token: str = Field(default="", alias="X_BEARER_TOKEN")

    chroma_persist_dir: str = Field(default="data/chroma", alias="CHROMA_PERSIST_DIR")
    publication_queue_dir: str = Field(
        default="publication_queue", alias="PUBLICATION_QUEUE_DIR"
    )
    knowledge_dir: str = Field(default="rag/knowledge", alias="KNOWLEDGE_DIR")

    schedule_hour: int = Field(default=8, alias="SCHEDULE_HOUR")
    schedule_minute: int = Field(default=0, alias="SCHEDULE_MINUTE")
    timezone: str = Field(default="Europe/Madrid", alias="TIMEZONE")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def chroma_path(self) -> Path:
        return PROJECT_ROOT / self.chroma_persist_dir

    @property
    def queue_path(self) -> Path:
        return PROJECT_ROOT / self.publication_queue_dir

    @property
    def knowledge_path(self) -> Path:
        return PROJECT_ROOT / self.knowledge_dir

    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    def has_pexels(self) -> bool:
        return bool(self.pexels_api_key)

    def has_meta(self) -> bool:
        return bool(self.meta_access_token and self.meta_instagram_account_id)

    def use_mock(self) -> bool:
        if self.demo_mode:
            return True
        return self.mock_mode and not self.has_openai()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml(relative_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
