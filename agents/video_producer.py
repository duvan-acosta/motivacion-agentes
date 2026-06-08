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

    def _build_script_prompt(
        self,
        message: str,
        theme: str,
        filosofia_ctx: list[str],
        guion_ctx: list[str],
    ) -> str:
        video_cfg = self.brand.get("video", {})
        min_s = video_cfg.get("min_duration_seconds", 20)
        max_s = video_cfg.get("max_duration_seconds", 40)
        filosofia = "\n---\n".join(filosofia_ctx[:3])
        guion = "\n---\n".join(guion_ctx[:4])
        return f"""Eres guionista de video corto reflexivo (Reels/Shorts/TikTok).
Voz de marca: serena, lúcida, sin clichés motivacionales.

Mensaje núcleo: {message}
Tema: {theme}
Duración objetivo: {min_s}-{max_s} segundos.
Cadencia de voz: 2.0-2.5 palabras/segundo (≈ 70-100 palabras totales).

Arquitectura narrativa que DEBES seguir (de la guía RAG):
{guion}

Filosofía de referencia (inspírate, no copies):
{filosofia}

Reglas duras:
- Cada salto de línea es un overlay independiente (máx 12 palabras por línea).
- Hook silencioso en los primeros 3 segundos (1 frase). Nada de gritar.
- Una sola idea en todo el video.
- Cierre que devuelva al espectador a sí mismo, sin CTA explícito.
- Prohibido: "vibras", "energías", "tu mejor versión", citas atribuidas.

Responde SOLO JSON válido:
{{"script": "frase 1\\nfrase 2\\nfrase 3\\n..."}}"""

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

        filosofia_ctx = self.rag.query("filosofia", f"sub-ángulo {theme} reflexión profunda")
        guion_ctx = self.rag.query("guion", f"arquitectura plantilla {theme}")
        try:
            script = self._call_llm_script(
                self._build_script_prompt(message, theme, filosofia_ctx, guion_ctx)
            )
            return {"script": script.strip(), "theme": theme, "message": message}
        except Exception as exc:
            logger.warning("Guion LLM falló: %s", exc)
            demo = pick_demo_content(theme)
            return {"script": demo.get("script", ""), "theme": theme, "message": message}

    def get_video_keywords(self, theme: str, visual_keywords: list[str]) -> list[str]:
        defaults = visual_keywords or ["nature vertical", "ocean waves", "forest"]
        return [f"{kw} vertical" if "vertical" not in kw else kw for kw in defaults[:2]]
