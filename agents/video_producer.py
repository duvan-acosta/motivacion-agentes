"""VideoProducerAgent — guion, TTS y especificaciones de video."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from rag.store import get_rag_store
from utils.config import get_settings, load_yaml
from utils.demo_mode import pick_demo_content

logger = logging.getLogger(__name__)


class VideoProducerAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rag = get_rag_store()
        self.brand = load_yaml("config/brand.yaml")

    def _build_script_prompt(self, message: str, theme: str, context: list[str]) -> str:
        video_cfg = self.brand.get("video", {})
        min_s = video_cfg.get("min_duration_seconds", 20)
        max_s = video_cfg.get("max_duration_seconds", 40)
        ctx = "\n".join(context[:4])
        return f"""Expande este mensaje en un guion de voz en off para video vertical motivacional.

Mensaje: {message}
Tema: {theme}
Duración objetivo: {min_s}-{max_s} segundos (~80-120 palabras)
Contexto: {ctx}

Reglas:
- Español sereno y profundo
- Frases cortas para overlays de texto
- Hook en las primeras 2 frases
- Cierre impactante
Responde SOLO JSON: {{"script": "texto con saltos de línea entre frases"}}"""

    def _call_llm_script(self, prompt: str) -> str:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0.7,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data.get("script", content)
        return content

    def produce_script(self, message: str, theme: str, existing_script: str = "") -> dict[str, Any]:
        if existing_script:
            return {"script": existing_script, "theme": theme, "message": message}

        if self.settings.demo_mode or self.settings.use_mock():
            demo = pick_demo_content(theme)
            return {"script": demo.get("script", ""), "theme": theme, "message": message}

        ctx = self.rag.query("filosofia", f"guion video {theme} narración")
        try:
            script = self._call_llm_script(self._build_script_prompt(message, theme, ctx))
            return {"script": script.strip(), "theme": theme, "message": message}
        except Exception as exc:
            logger.warning("Guion LLM falló: %s", exc)
            demo = pick_demo_content(theme)
            return {"script": demo.get("script", ""), "theme": theme, "message": message}

    def get_video_keywords(self, theme: str, visual_keywords: list[str]) -> list[str]:
        defaults = visual_keywords or ["nature vertical", "ocean waves", "forest"]
        return [f"{kw} vertical" if "vertical" not in kw else kw for kw in defaults[:2]]
