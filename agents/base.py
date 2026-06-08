"""Estado compartido del grafo LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    theme: str
    content_id: str
    message: str
    caption: str
    hashtags: list[str]
    visual_keywords: list[str]
    visual_spec: dict[str, Any]
    script: str
    audio_path: str
    images: dict[str, str]
    video_path: str
    package_path: str
    metadata: dict[str, Any]
    errors: list[str]
    status: str
