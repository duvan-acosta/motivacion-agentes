"""ContentCreatorAgent — mensaje, caption y hashtags en español."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from rag.store import get_rag_store
from utils.config import get_settings, load_yaml
from utils.demo_mode import pick_demo_content

logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rag = get_rag_store()
        self.brand = load_yaml("config/brand.yaml")

    def _build_prompt(
        self,
        theme: str,
        filosofia_ctx: list[str],
        brand_ctx: list[str],
        algoritmo_ctx: list[str],
    ) -> str:
        base_tags = self.brand.get("hashtags_base", [])
        filosofia = "\n---\n".join(filosofia_ctx[:4])
        brand = "\n---\n".join(brand_ctx[:4])
        algoritmo = "\n---\n".join(algoritmo_ctx[:2])
        return f"""Eres redactor de Reflexiones Serenas, una marca de filosofía
práctica en español. Tono: sereno, lúcido, sin clichés motivacionales.

Tema del día: {theme}

Filosofía de referencia (inspírate, NO cites literalmente):
{filosofia}

Voz de marca y plantillas (hooks, cierres, vocabulario):
{brand}

Señales de algoritmo a tener en cuenta para Instagram:
{algoritmo}

Reglas innegociables:
- ORIGINALIDAD: nada de citas atribuidas (Buda, Marco Aurelio, Einstein…).
- PROHIBIDAS literalmente: "vibras", "energías", "manifestar", "tu mejor versión",
  "todo pasa por algo", "el cielo es el límite", "cree en ti".
- El mensaje (imagen) usa una de las estructuras: observación+pregunta, antítesis,
  imagen+aplicación, o replanteo de sentido común. 15-40 palabras.
- El caption sigue el patrón: hook (1 línea) → desarrollo (2-4 líneas, una idea
  por línea) → aplicación/pregunta concreta (1 línea). Sin emojis decorativos.
- visual_keywords: 3 términos en INGLÉS para búsqueda en Pexels (un sujeto, un
  ambiente, un detalle). Sin rostros frontales, sin gente sonriendo a cámara.

Responde SOLO con JSON válido (sin texto fuera del JSON):
{{
  "message": "mensaje principal 15-40 palabras",
  "caption": "caption 4 bloques cortos separados por saltos de línea dobles",
  "hashtags": ["#tag1", "#tag2", ...],
  "visual_keywords": ["en_keyword_1", "en_keyword_2", "en_keyword_3"]
}}

Hashtags: 12-15, mezclando amplios + medios + nicho. Sin tildes. Incluye
2-3 del set base de marca: {', '.join(base_tags[:5])}."""

    def _parse_llm_response(self, text: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Respuesta LLM sin JSON válido")

    def _call_llm(self, prompt: str) -> dict[str, Any]:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0.8,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        return self._parse_llm_response(content)

    def generate(self, theme: str, content_id: str | None = None) -> dict[str, Any]:
        if self.settings.demo_mode or self.settings.use_mock():
            demo = pick_demo_content(theme)
            return {
                "theme": demo["theme"],
                "content_id": content_id or demo["content_id"],
                "message": demo["message"],
                "caption": demo["caption"],
                "hashtags": demo["hashtags"],
                "visual_keywords": demo["visual_keywords"],
                "script": demo.get("script", ""),
            }

        filosofia_ctx = self.rag.query(
            "filosofia", f"{theme} sub-ángulo patrón mensaje original"
        )
        brand_ctx = self.rag.query(
            "brand", "hook caption cierre vocabulario plantilla hashtags"
        )
        algoritmo_ctx = self.rag.query(
            "algoritmo", "Instagram save share hook hashtags mix nicho"
        )

        try:
            data = self._call_llm(
                self._build_prompt(theme, filosofia_ctx, brand_ctx, algoritmo_ctx)
            )
            return {
                "theme": theme,
                "content_id": content_id,
                "message": data["message"],
                "caption": data["caption"],
                "hashtags": data.get("hashtags", []),
                "visual_keywords": data.get("visual_keywords", [theme]),
                "script": "",
            }
        except Exception as exc:
            logger.warning("LLM falló, usando demo: %s", exc)
            demo = pick_demo_content(theme)
            return {
                "theme": theme,
                "content_id": content_id or demo["content_id"],
                "message": demo["message"],
                "caption": demo["caption"],
                "hashtags": demo["hashtags"],
                "visual_keywords": demo["visual_keywords"],
                "script": demo.get("script", ""),
            }
