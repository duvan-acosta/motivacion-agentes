"""Estado compartido del grafo LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    theme: str
    content_id: str
    message: str
    message_alt: str  # variante para A/B test
    caption: str
    caption_instagram: str
    caption_facebook: str
    caption_tiktok: str
    caption_youtube: str
    title_youtube: str
    tweet: str
    hashtags: list[str]
    visual_keywords: list[str]
    visual_spec: dict[str, Any]
    script: str
    audio_path: str
    images: dict[str, str]
    video_path: str
    package_path: str
    metadata: dict[str, Any]
    trend_data: dict[str, Any]
    errors: list[str]
    status: str
    publish_results: dict[str, Any]
    published_platforms: list[str]
