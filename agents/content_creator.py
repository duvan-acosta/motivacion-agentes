"""ContentCreatorAgent — mensaje, caption y hashtags en español."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from rag.store import get_rag_store
from utils.config import get_settings, load_yaml
from utils.demo_mode import pick_demo_content
from utils.products import cta_context_for_prompt

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

        cta = cta_context_for_prompt()
        if cta.get("has_product"):
            cta_block = f"""
Producto activo a promover suavemente al final del caption (NO en el mensaje
de imagen, NO en hashtags):
- Nombre: {cta['product_name']}
- Cómo nombrarlo en el texto: "{cta['product_short_name']}"
- Descripción: {cta['product_description']}
- Estilo de CTA: {cta['cta_style']}

El cierre del caption debe invitar (sin agresividad, manteniendo voz de marca)
a conocer el producto. La URL la añade el sistema; tú solo escribes la
invitación. No uses imperativos huecos como "¡compra ya!" ni "no te lo pierdas".
"""
        else:
            cta_block = ""
        return f"""Eres redactor de Mental Equilibrio, marca de motivación
DIRECTA Y EMOCIONAL dirigida a audiencia LATINOAMERICANA (Colombia, México,
Perú, Chile, Argentina, Centroamérica).

ESTILO obligatorio: voz amiga que LEVANTA. Cálida, directa, esperanzadora.
NO eres un filósofo. NO eres un mentor sereno. Eres una voz que abraza al
lector y le recuerda que va a estar bien. Estilo Mel Robbins, Marisa Peer,
Marian Rojas — con sabor latino.

CRÍTICO — tono emocional:
- Habla EN SEGUNDA PERSONA, tú a tú. "Hoy puedes…", "Mereces…",
  "Recuerda esto:", "Está bien sentirte así".
- VALIDA emociones difíciles antes de animar. "Está bien estar cansado".
- Termina con esperanza visible. Nada de cierres tristes ni puramente
  reflexivos. El lector debe sentirse MEJOR que antes de leer.
- Permitido (en moderación): 1 exclamación máximo por mensaje, emojis 0.
- Cálido, accesible, sin academia ni metáforas crípticas.

CRÍTICO — lenguaje LATINO:
- Sin peninsular: nada de "pillar", "majo", "flipar", "vale", "tío".
- Tuteo. Nunca "vosotros".
- "Agarrar" mejor que "coger".
- Si añades una escena, que sea LATINA cotidiana: café de la mañana,
  audio de mamá en WhatsApp, tráfico, bus/micro, la quincena, despertar
  cansado. UNA escena solo, breve.

CRÍTICO — anti-cringe (prohibido):
- "Vibras", "energías", "manifestar", "ley de atracción", "abundancia".
- "Tu mejor versión", "sé positivo siempre".
- "Todo pasa por algo", "el universo conspira".
- Citas atribuidas a Buda, Einstein, Marco Aurelio, Confucio.

CRÍTICO — variedad de estructura (rota entre estas):
- Afirmación directa: "Hoy puedes…"
- Validación + paso pequeño: "Está bien que… Tómate un ratico para…"
- Recordatorio cariñoso: "Recuerda esto: …"
- Pregunta abierta esperanzadora: "¿Y si hoy…?"
- Inversión amable: "No te falta X. Te falta Y. Date permiso de Z."
- Mini-escena latina + cierre cálido.

NO repitas la estructura "X no es Y, es Z" del autor reflexivo viejo.

Tema del día: {theme}

Filosofía de referencia (inspírate, NO cites literalmente):
{filosofia}

Voz de marca y plantillas (hooks, cierres, vocabulario):
{brand}

Señales de algoritmo a tener en cuenta para Instagram:
{algoritmo}
{cta_block}
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

Responde SOLO con JSON válido (sin texto fuera del JSON), con captions
adaptados a cada plataforma:

{{
  "message": "mensaje principal de la imagen, 15-40 palabras",
  "message_alt": "VARIANTE alternativa del mensaje, MISMO TEMA pero hook distinto, 15-40 palabras",
  "caption_instagram": "caption largo IG: hook + 3-4 párrafos cortos + CTA cariñoso + 12-15 hashtags al final",
  "caption_facebook": "caption FB conversacional, frases largas, 2-3 hashtags. Sin emojis. Pedir compartir explícito",
  "caption_tiktok": "caption TikTok CORTO: hook + 1 línea de aliento + 4-6 hashtags. Máx 200 caracteres antes de hashtags",
  "title_youtube": "título YouTube Short ≤60 caracteres, gancho directo emocional",
  "caption_youtube": "descripción YouTube: hook + 2-3 párrafos + CTA + #Shorts al final",
  "tweet": "tweet único ≤200 caracteres (deja espacio para la URL con UTM que añade el sistema), 0-2 hashtags",
  "hashtags": ["#tag1", "#tag2", ...],
  "visual_keywords": ["en_keyword_1", "en_keyword_2", "en_keyword_3"]
}}

Reglas por plataforma (alineadas con RAG de algoritmo):
- INSTAGRAM: tono cálido reflexivo, pide guardar > pide compartir, sin emojis.
- FACEBOOK: ligeramente más conversacional, frases más largas, "Compartelo con
  alguien que necesite leerlo" funciona muy bien aquí.
- TIKTOK: hook visual va en el video, el caption es solo apoyo corto.
- YOUTUBE: descripción tipo IG + obligatorio #Shorts al final.
- X/TWITTER: tweet AUTÓNOMO ≤200 chars (el sistema añade ~80 chars de URL+UTM).

Hashtags principales: 12-15, sin tildes. Incluye 2-3 del set base de marca:
{', '.join(base_tags[:5])}.

El "message_alt" sirve para A/B test: misma temática, otro hook (si el
principal usa "Hoy puedes…", el alt usa "Está bien que…" o "Recuerda esto:")."""

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
            temperature=0.8,
            **self.settings.llm_kwargs(),
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
                "message_alt": data.get("message_alt", ""),
                # caption "legacy" para compatibilidad (usa el de IG por defecto)
                "caption": data.get("caption_instagram") or data.get("caption", ""),
                "caption_instagram": data.get("caption_instagram", ""),
                "caption_facebook": data.get("caption_facebook", ""),
                "caption_tiktok": data.get("caption_tiktok", ""),
                "caption_youtube": data.get("caption_youtube", ""),
                "title_youtube": data.get("title_youtube", ""),
                "tweet": data.get("tweet", ""),
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
                "message_alt": "",
                "caption": demo["caption"],
                "caption_instagram": demo["caption"],
                "caption_facebook": demo["caption"],
                "caption_tiktok": demo["message"],
                "caption_youtube": demo["caption"],
                "title_youtube": demo["message"][:60],
                "tweet": demo["message"][:200],
                "hashtags": demo["hashtags"],
                "visual_keywords": demo["visual_keywords"],
                "script": demo.get("script", ""),
            }
