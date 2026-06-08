"""Modo demo/offline con contenido de ejemplo sin APIs."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

DEMO_MESSAGES = [
    {
        "theme": "resiliencia",
        "message": "No controlas la tormenta, pero sí el timón de tu actitud.",
        "visual_keywords": ["mountain peak", "storm clearing", "ocean waves"],
        "caption": (
            "¿Cuántas veces la adversidad te hizo más fuerte de lo que creías posible?\n\n"
            "La resiliencia no es negar la dificultad: es elegir seguir adelante con propósito.\n\n"
            "Hoy, recuerda: ya has superado el 100% de tus peores días."
        ),
        "hashtags": [
            "#resiliencia",
            "#estoicismo",
            "#motivacion",
            "#filosofia",
            "#reflexion",
            "#crecimientopersonal",
            "#vidaconsciente",
            "#fuerzainterior",
        ],
    },
    {
        "theme": "calma",
        "message": "El silencio entre pensamientos es donde a veces encontramos la respuesta más clara.",
        "visual_keywords": ["calm ocean", "peaceful lake", "misty forest"],
        "caption": (
            "En un mundo que premia el ruido, la calma es un acto de rebeldía.\n\n"
            "No necesitas resolver todo ahora. Respira. El momento presente es suficiente.\n\n"
            "¿Cuándo fue la última vez que te regalaste cinco minutos de silencio?"
        ),
        "hashtags": [
            "#calma",
            "#mindfulness",
            "#pazinterior",
            "#filosofia",
            "#reflexion",
            "#presencia",
            "#meditacion",
            "#serenidad",
        ],
    },
    {
        "theme": "claridad",
        "message": "Menos ruido, más dirección. La claridad llega cuando dejas de perseguirlo todo.",
        "visual_keywords": ["sunrise", "golden hour", "open sky"],
        "caption": (
            "La confusión suele venir de querer demasiadas cosas a la vez.\n\n"
            "Elige una dirección. Da un paso. La claridad se construye en el movimiento.\n\n"
            "¿Qué puedes simplificar hoy?"
        ),
        "hashtags": [
            "#claridad",
            "#proposito",
            "#enfoque",
            "#filosofia",
            "#motivacion",
            "#minimalismo",
            "#decisiones",
            "#sabiduria",
        ],
    },
]

DEMO_SCRIPTS = [
    (
        "A veces creemos que necesitamos tenerlo todo resuelto antes de actuar.\n\n"
        "Pero la verdad es más simple.\n\n"
        "No controlas la tormenta. Solo controlas cómo navegas.\n\n"
        "Hoy, elige un paso pequeño. Eso es suficiente."
    ),
    (
        "El silencio no es vacío.\n\n"
        "Es el espacio donde la mente encuentra dirección.\n\n"
        "Detente un momento. Respira.\n\n"
        "La respuesta que buscas quizá ya está dentro de ti."
    ),
]


def pick_demo_content(theme: str | None = None) -> dict[str, Any]:
    items = DEMO_MESSAGES
    if theme:
        filtered = [m for m in items if m["theme"] == theme]
        if filtered:
            items = filtered
    base = random.choice(items)
    script = random.choice(DEMO_SCRIPTS)
    return {
        **base,
        "script": script,
        "content_id": f"demo_{base['theme']}_{datetime.now().strftime('%H%M%S')}",
        "generated_at": datetime.now().isoformat(),
        "mode": "demo",
    }


def demo_youtube_meta(message: str, theme: str) -> dict[str, str]:
    return {
        "title": f"{message[:60]}..." if len(message) > 60 else message,
        "description": (
            f"Reflexión sobre {theme}.\n\n"
            "Suscríbete para más contenido filosófico y motivacional.\n\n"
            "#Shorts #filosofia #motivacion"
        ),
        "tags": "filosofia,estoicismo,motivacion,reflexion,shorts," + theme,
    }


def demo_tweet(message: str, theme: str) -> str:
    tags = f"#{theme} #filosofia #reflexion"
    text = f"{message}\n\n{tags}"
    return text[:280]
