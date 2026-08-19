"""TrendAgent — detecta temas y ángulos trending antes de generar contenido."""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Ángulos con máxima resonancia emocional por tema — priorizan saves + shares
_ANGLES: dict[str, list[str]] = {
    "ansiedad_cotidiana": [
        "el cansancio que no es físico",
        "cuando tu mente no para aunque estés quieto",
        "por qué no puedes 'simplemente relajarte'",
        "el síntoma de ansiedad que nadie te dijo",
    ],
    "amor_propio": [
        "por qué es tan difícil hablarte bien",
        "el día que dejaste de pedirte perdón por existir",
        "amarte no es un logro, es una práctica diaria",
        "lo que pasa cuando por fin paras de compararte",
    ],
    "resiliencia": [
        "la diferencia entre aguantar y sanar",
        "cuando la vida no sale como planeaste",
        "cómo te levantas sin fingir que no te caíste",
        "lo que te hace fuerte no es no caer — es volver",
    ],
    "calma": [
        "lo que pasa en tu cerebro cuando respiras profundo",
        "por qué la calma se practica, no se encuentra",
        "el hábito de 2 minutos que cambia tu día",
        "qué hacer cuando todo te satura",
    ],
    "esperanza": [
        "el día que todo cambió sin que lo notaras",
        "por qué seguir cuando no ves el resultado",
        "una señal de que vas por buen camino aunque duela",
        "lo que viene después del momento más difícil",
    ],
    "autoestima": [
        "el momento en que te das cuenta de tu valor",
        "por qué buscas aprobación y cómo parar",
        "lo que otros ven en ti que tú no ves",
        "cuando empiezas a creer en ti sin necesitar pruebas",
    ],
    "propósito": [
        "cómo encontrar dirección cuando estás perdido",
        "la diferencia entre metas y propósito de vida",
        "señales de que ya estás en el camino correcto",
        "por qué el propósito no se encuentra — se construye",
    ],
    "coraje": [
        "hacer lo que te da miedo de todas formas",
        "cuando el miedo y la acción coexisten",
        "la valentía silenciosa que nadie aplaude",
        "lo que pasa después de dar el primer paso",
    ],
    "soledad_saludable": [
        "aprender a estar contigo sin escaparte",
        "la diferencia entre estar solo y sentirte solo",
        "cuando la soledad deja de doler",
        "por qué tu propia compañía importa",
    ],
    "limites": [
        "cuando decir no es un acto de amor",
        "por qué poner límites te da culpa y cómo manejarlo",
        "lo que pierdes cuando no defiendes tu energía",
        "cómo decir no sin perder la relación",
    ],
    "gratitud": [
        "la gratitud que va más allá de las 'cosas buenas'",
        "agradecer incluso los días difíciles",
        "por qué practicar gratitud cambia tu cerebro",
        "cuando empiezas a ver lo que ya tienes",
    ],
    "empezar_de_nuevo": [
        "cuando todo se derrumba y eso es el comienzo",
        "los primeros días después de una pérdida grande",
        "cómo reinventarte sin borrarte",
        "la libertad de los comienzos que duelen",
    ],
}

# Días con mayor engagement para contenido emocional (basado en datos LATAM)
_PEAK_THEMES_BY_WEEKDAY: dict[int, list[str]] = {
    0: ["esperanza", "propósito", "coraje"],           # Lunes — inicio de semana
    1: ["ansiedad_cotidiana", "calma", "limites"],     # Martes
    2: ["amor_propio", "autoestima", "resiliencia"],   # Miércoles — midweek dip
    3: ["propósito", "coraje", "empezar_de_nuevo"],    # Jueves
    4: ["esperanza", "gratitud", "amor_propio"],       # Viernes — reflexión weekend
    5: ["calma", "soledad_saludable", "gratitud"],     # Sábado
    6: ["esperanza", "empezar_de_nuevo", "propósito"], # Domingo — nuevo comienzo
}

# Formatos con mayor tasa de saves por plataforma
_HIGH_SAVE_FORMATS = [
    "lista_corta",      # "3 señales de que..."
    "dato_revelador",   # "Lo que nadie te dice sobre..."
    "herramienta",      # "Haz esto cuando sientas..."
    "pregunta_espejo",  # "¿Cuándo fue la última vez que...?"
    "antes_despues",    # "Antes pensaba X. Ahora sé Y."
    "permiso",          # "Está bien que..."
]


def _try_google_trends(theme: str, geo: str = "CO") -> list[str]:
    """Intenta obtener hashtags relacionados via pytrends (sin API key)."""
    try:
        from pytrends.request import TrendReq

        kw_map = {
            "ansiedad_cotidiana": "ansiedad",
            "amor_propio": "amor propio",
            "resiliencia": "resiliencia",
            "calma": "calma mental",
            "esperanza": "esperanza",
            "autoestima": "autoestima",
            "propósito": "proposito de vida",
            "coraje": "valentía",
            "soledad_saludable": "soledad",
            "limites": "límites personales",
            "gratitud": "gratitud",
            "empezar_de_nuevo": "empezar de nuevo",
        }
        kw = kw_map.get(theme, theme.replace("_", " "))
        pt = TrendReq(hl="es-CO", tz=-300, timeout=(5, 10))
        pt.build_payload([kw], cat=0, timeframe="now 7-d", geo=geo)
        related = pt.related_queries()
        rising = related.get(kw, {}).get("rising")
        if rising is not None and not rising.empty:
            queries = rising["query"].head(5).tolist()
            tags = [f"#{q.replace(' ', '').lower()}" for q in queries if len(q) < 25]
            logger.info("[trend] Google Trends OK — %d tags rising", len(tags))
            return tags[:4]
    except Exception as exc:
        logger.debug("[trend] pytrends no disponible: %s", exc)
    return []


class TrendAgent:
    """Analiza tendencias y selecciona el ángulo con mayor potencial viral."""

    def analyze(
        self,
        theme: str | None = None,
        platform: str = "all",
    ) -> dict[str, Any]:
        weekday = datetime.now().weekday()
        hour = datetime.now().hour

        # Seleccionar tema con mayor potencial hoy
        if theme:
            selected_theme = theme
        else:
            candidates = _PEAK_THEMES_BY_WEEKDAY.get(weekday, list(_ANGLES.keys()))
            selected_theme = random.choice(candidates)

        # Ángulo con mayor probabilidad de save/share
        angles = _ANGLES.get(selected_theme, [selected_theme])
        trending_angle = random.choice(angles)

        # Formato óptimo según hora y día
        save_format = random.choice(_HIGH_SAVE_FORMATS)

        # Hashtags trending (Google Trends + base)
        geo = "CO"  # Colombia — mayor base de seguidores
        trending_tags = _try_google_trends(selected_theme, geo=geo)

        # Contexto de monetización por plataforma
        platform_focus = self._platform_context(platform, hour, weekday)

        return {
            "theme": selected_theme,
            "trending_angle": trending_angle,
            "save_format": save_format,
            "trending_hashtags": trending_tags,
            "platform_focus": platform_focus,
            "weekday": weekday,
            "peak_hour": hour,
        }

    def _platform_context(self, platform: str, hour: int, weekday: int) -> dict[str, str]:
        contexts = {
            "instagram": (
                "Prioridad: SAVES. Hook que detenga el scroll. "
                "Formato lista o herramienta concreta. "
                "CTA: 'Guarda esto para cuando lo necesites.'"
            ),
            "tiktok": (
                "Prioridad: RETENCIÓN PRIMEROS 3 SEGUNDOS. "
                "Hook visual-emocional inmediato. "
                "CTA al final: 'Sígueme para más' o pregunta que genere comentarios."
            ),
            "facebook": (
                "Prioridad: COMPARTIR. Texto conversacional, pregunta al final. "
                "CTA: 'Comparte con alguien que necesite leer esto hoy.'"
            ),
            "all": (
                "Optimizar para saves en Instagram, retención en TikTok, "
                "shares en Facebook. Hook universal que funcione en las 3."
            ),
        }
        return {"instruction": contexts.get(platform, contexts["all"])}
