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

    def _build_prompt(self, theme: str, context: list[str]) -> str:
        ctx = "\n---\n".join(context[:6])
        base_tags = self.brand.get("hashtags_base", [])
        return f"""Eres un creador de contenido filosófico-motivacional en español.

Tema del día: {theme}

Contexto RAG (filosofía y tono de marca):
{ctx}

Genera contenido ORIGINAL (no copies citas textuales de autores). Responde SOLO con JSON válido:
{{
  "message": "mensaje principal 15-40 palabras para imagen",
  "caption": "caption para Instagram 3-5 párrafos cortos",
  "hashtags": ["#tag1", "#tag2", ...],
  "visual_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Hashtags base sugeridos: {', '.join(base_tags[:5])}
Incluye 8-15 hashtags. Tono sereno, profundo, accesible."""

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

        filosofia_ctx = self.rag.query("filosofia", f"tema {theme} estoicismo mensaje motivacional")
        brand_ctx = self.rag.query("brand", "tono caption hashtags español")
        context = filosofia_ctx + brand_ctx

        try:
            data = self._call_llm(self._build_prompt(theme, context))
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
