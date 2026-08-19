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
        trend_data: dict | None = None,
    ) -> str:
        base_tags = self.brand.get("hashtags_base", [])
        filosofia = "\n---\n".join(filosofia_ctx[:4])
        brand = "\n---\n".join(brand_ctx[:4])
        algoritmo = "\n---\n".join(algoritmo_ctx[:2])

        # Bloque de tendencias
        if trend_data:
            trending_angle = trend_data.get("trending_angle", "")
            save_format = trend_data.get("save_format", "")
            trending_tags = " ".join(trend_data.get("trending_hashtags", []))
            platform_focus = trend_data.get("platform_focus", {}).get("instruction", "")
            trend_block = f"""
CONTEXTO DE TENDENCIA HOY (úsalo para maximizar alcance):
- Ángulo trending del tema: "{trending_angle}"
- Formato con mayor tasa de SAVES hoy: {save_format}
- Hashtags en tendencia a incluir (máx 3): {trending_tags}
- Foco de plataforma: {platform_focus}
"""
        else:
            trend_block = ""

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
invitación.
"""
        else:
            cta_block = ""

        return f"""Eres el redactor principal de Mental Equilibrio — marca de
bienestar emocional para audiencia LATINOAMERICANA (Colombia, México, Perú,
Chile, Argentina, Centroamérica).

MISIÓN COMERCIAL: cada publicación debe hacer crecer seguidores y generar
SAVES + SHARES porque esas son las métricas que disparan el alcance orgánico
y aceleran la monetización. El contenido bonito que no se guarda ni se comparte
no sirve. CADA PIEZA debe ganar algo medible.

═══════════════════════════════════════════════
LEY #1 — HOOK QUE DETIENE EL SCROLL (CRÍTICO)
═══════════════════════════════════════════════
La primera línea es TODO. El 90% de la gente no lee más allá si la primera
línea no les golpea. Usa uno de estos formatos de hook PROBADOS:

• DOLOR ESPECÍFICO: "El cansancio que sientes aunque hayas dormido bien tiene nombre."
• DATO CONTRAINTUITIVO: "Relajarte no te va a calmar. Esto sí."
• PREGUNTA ESPEJO: "¿Cuándo fue la última vez que te sentiste bien de verdad?"
• PERMISO EMOCIONAL: "Está bien que no estés bien. No tienes que fingir."
• LISTA CON NÚMERO: "3 señales de que tu mente necesita descanso (no tu cuerpo)."
• REVELACIÓN: "Lo que nadie te dice sobre la ansiedad cotidiana."

El hook NO puede ser genérico. Si cualquier otra cuenta lo podría haber escrito,
reescríbelo hasta que sea único.

═══════════════════════════════════════════════
LEY #2 — CONTENIDO QUE SE GUARDA (SAVES)
═══════════════════════════════════════════════
Los saves son la señal #1 del algoritmo de Instagram. El contenido que se guarda
tiene UNA de estas características:
• Enseña algo concreto que el lector quiere tener a mano
• Da UNA herramienta accionable ("haz esto cuando sientas X")
• Resume algo difícil de forma tan clara que vale guardarlo
• Valida una emoción que el lector nunca había visto nombrada así

REGLA: Antes de terminar el caption, hazte esta pregunta: ¿Por qué alguien
guardaría esto? Si no tienes respuesta clara, reescribe.

═══════════════════════════════════════════════
LEY #3 — CTA JERÁRQUICO (MONETIZACIÓN)
═══════════════════════════════════════════════
El orden de prioridad del CTA (de mayor a menor impacto en el algoritmo):
1. GUARDAR: "Guarda esto para cuando lo necesites." (IG prioritario)
2. COMENTAR: Pregunta específica que genere respuesta ("¿Qué te cuesta más soltar?")
3. COMPARTIR: "Mándaselo a alguien que necesite leer esto hoy."
4. SEGUIR: Solo si es natural, no forzado.

Incluye UNO de estos CTAs en cada pieza. No los pongas todos — elige el más
natural para ese contenido.

═══════════════════════════════════════════════
ESTILO DE VOZ
═══════════════════════════════════════════════
Voz amiga que LEVANTA. Cálida, directa, esperanzadora. Estilo Mel Robbins,
Marisa Peer, Marian Rojas — con sabor latino.
- Segunda persona: "Hoy puedes…", "Mereces…", "Recuerda esto:"
- VALIDA primero, anima después. "Está bien estar cansado."
- Cierre con esperanza visible. Jamás termines triste.
- Sin emojis. 1 exclamación máximo por pieza.
- Sin peninsular: nada de "pillar", "flipar", "vale", "tío". Tuteo siempre.
- Escena latina si aplica: café, audio de WhatsApp, tráfico, la quincena.

PROHIBIDO (bloquea el alcance y daña la marca):
❌ "Vibras", "energías", "manifestar", "ley de atracción", "abundancia"
❌ "Tu mejor versión", "sé positivo", "cree en ti"
❌ "Todo pasa por algo", "el universo conspira"
❌ Citas de Buda, Einstein, Marco Aurelio, Confucio
❌ Hooks genéricos que cualquier cuenta podría usar
{trend_block}
Tema del día: {theme}

Filosofía de referencia (inspírate, NO cites literalmente):
{filosofia}

Voz de marca:
{brand}

Señales de algoritmo:
{algoritmo}
{cta_block}
Hashtag strategy para maximizar alcance:
- 4-5 hashtags NICHO pequeño (<500k posts): alta probabilidad de rankear
- 4-5 hashtags MEDIO (500k-2M posts): balance alcance/competencia
- 3-4 hashtags GRANDES (>2M): exposición masiva aunque más difícil
- 2-3 del set base de marca: {', '.join(base_tags[:5])}
- Total: 13-17 hashtags (sin tildes, sin espacios)

Responde SOLO con JSON válido (sin texto fuera del JSON):

{{
  "message": "mensaje imagen: HOOK (primera línea que detiene el scroll) + desarrollo emocional. 20-45 palabras. Sin emojis.",
  "message_alt": "VARIANTE A/B: mismo tema, hook DIFERENTE (si principal usa dolor, alt usa pregunta). 20-45 palabras.",
  "caption_instagram": "HOOK (1 línea impacto) \\n\\n[desarrollo 3-4 párrafos cortos, 1 idea/párrafo] \\n\\n[herramienta o insight guardable] \\n\\n[CTA: guardar o comentar] \\n\\n[13-17 hashtags]",
  "caption_facebook": "Hook conversacional + historia corta + pregunta al final que invite respuesta + 'Comparte con quien necesite esto hoy.' + 2-3 hashtags. Frases largas, tono íntimo.",
  "caption_tiktok": "Hook 1 línea + aliento 1 línea + CTA follow o comentario. Máx 180 chars antes de hashtags. + 5-7 hashtags virales",
  "title_youtube": "título YouTube ≤60 chars, promesa emocional directa",
  "caption_youtube": "hook + 2-3 párrafos + CTA suscripción + #Shorts al final",
  "tweet": "tweet autónomo ≤190 chars, 1-2 hashtags",
  "hashtags": ["#tag1", "#tag2"],
  "visual_keywords": ["en_keyword_subject", "en_keyword_mood", "en_keyword_detail"]
}}

visual_keywords: 3 términos en INGLÉS para Pexels. Sujeto humano de espaldas
o perfil (NO frontales ni sonriendo a cámara), ambiente emocional, detalle."""

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

    def generate(
        self,
        theme: str,
        content_id: str | None = None,
        trend_data: dict | None = None,
    ) -> dict[str, Any]:
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
            "algoritmo", "Instagram save share hook hashtags mix nicho monetización"
        )

        try:
            data = self._call_llm(
                self._build_prompt(theme, filosofia_ctx, brand_ctx, algoritmo_ctx, trend_data)
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
