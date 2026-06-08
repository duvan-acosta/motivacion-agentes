"""DirectorAgent — orquesta temas, calendario y flujo."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from utils.config import get_settings, load_yaml


class DirectorAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.brand = load_yaml("config/brand.yaml")

    def pick_theme(self, override: str | None = None) -> str:
        if override:
            return override
        themes = self.brand.get("content", {}).get("themes_rotation", [])
        if not themes:
            themes = ["resiliencia", "calma", "claridad"]
        return random.choice(themes)

    def create_content_id(self, theme: str) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        suffix = datetime.now().strftime("%H%M%S")
        return f"msg_{date_str}_{theme}_{suffix}"

    def plan(self, theme: str | None = None) -> dict[str, Any]:
        selected = self.pick_theme(theme)
        content_id = self.create_content_id(selected)
        return {
            "theme": selected,
            "content_id": content_id,
            "planned_at": datetime.now().isoformat(),
            "brand": self.brand.get("brand", {}).get("name", "Reflexiones Serenas"),
        }
