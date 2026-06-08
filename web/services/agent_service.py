"""Servicio de agentes y tareas en background."""

from __future__ import annotations

import logging
from typing import Any

from graph.workflow import MotivacionWorkflow, run_generation
from web.services import state

logger = logging.getLogger(__name__)

AGENTS = [
    {
        "id": "director",
        "name": "DirectorAgent",
        "label": "Director",
        "description": "Orquesta temas, calendario editorial e identificadores de contenido.",
        "rag": [],
    },
    {
        "id": "content_creator",
        "name": "ContentCreatorAgent",
        "label": "Creador de contenido",
        "description": "Genera mensajes, captions y hashtags en español con tono filosófico-motivacional.",
        "rag": ["filosofia-es.md", "brand-voice.md"],
    },
    {
        "id": "visual_designer",
        "name": "VisualDesignerAgent",
        "label": "Diseñador visual",
        "description": "Define fondos, tipografía y composición visual por tema.",
        "rag": ["temas-visuales.md", "brand-voice.md"],
    },
    {
        "id": "video_producer",
        "name": "VideoProducerAgent",
        "label": "Productor de video",
        "description": "Expande mensajes en guiones de voz en off y especificaciones de video vertical.",
        "rag": ["filosofia-es.md", "brand-voice.md"],
    },
    {
        "id": "publisher",
        "name": "PublisherAgent",
        "label": "Publicador",
        "description": "Empaqueta assets por plataforma y genera manifest/status.",
        "rag": ["platforms-specs.yaml"],
    },
]

AGENT_SEQUENCE = [
    ("director", "Director"),
    ("content_creator", "Contenido"),
    ("visual_designer", "Visual"),
    ("video_producer", "Video"),
    ("publisher", "Empaquetado"),
]


def list_agents() -> list[dict[str, Any]]:
    statuses = state.get_agent_status()
    last_run = state.get_last_run()
    result = []
    for agent in AGENTS:
        item = dict(agent)
        item["status"] = statuses.get(agent["id"], "idle")
        if last_run and last_run.get("agent") == agent["id"]:
            item["last_run"] = {
                "theme": last_run.get("theme"),
                "timestamp": last_run.get("timestamp"),
                "success": last_run.get("success"),
                "message": last_run.get("message"),
            }
        result.append(item)
    return result


def run_generation_task(theme: str | None = None, demo: bool | None = None) -> None:
    if state.is_generation_running():
        logger.warning("Generación ya en curso")
        return

    state.set_generation_running(True)
    state.add_activity("Iniciando generación de contenido…", kind="generate")

    try:
        state.apply_demo_for_job(demo)
        for agent_id, label in AGENT_SEQUENCE:
            state.set_agent_status(agent_id, "running")
            state.set_last_run(
                {
                    "agent": agent_id,
                    "theme": theme or "automático",
                    "timestamp": state._now(),
                    "success": None,
                    "message": f"Ejecutando {label}…",
                }
            )

        result = run_generation(theme)

        for agent_id, _ in AGENT_SEQUENCE:
            state.set_agent_status(agent_id, "idle")

        errors = result.get("errors", [])
        success = not errors
        state.set_last_run(
            {
                "agent": "publisher",
                "theme": result.get("theme"),
                "timestamp": state._now(),
                "success": success,
                "message": result.get("message", "")[:120],
                "package_path": result.get("package_path"),
            }
        )

        if success:
            state.add_activity(
                f"Paquete generado: {result.get('package_path', '—')}",
                kind="success",
                meta={"theme": result.get("theme")},
            )
        else:
            state.set_agent_status("publisher", "error")
            state.add_activity(
                f"Generación con errores: {errors}",
                kind="error",
            )
    except Exception as exc:
        logger.exception("Error en generación")
        state.set_all_agents("error")
        state.set_last_run(
            {
                "agent": "director",
                "theme": theme,
                "timestamp": state._now(),
                "success": False,
                "message": str(exc),
            }
        )
        state.add_activity(f"Error en generación: {exc}", kind="error")
    finally:
        state.set_generation_running(False)
        state.set_all_agents("idle")


def run_full_workflow_task(theme: str | None = None, demo: bool | None = None) -> None:
    """Alias del workflow completo (generación end-to-end)."""
    run_generation_task(theme=theme, demo=demo)


def run_publish_task(package_id: str, platforms: list[str] | None = None) -> None:
    from web.services.content_service import resolve_package_path

    if state.is_publish_running(package_id):
        return

    state.set_publish_running(package_id, True)
    state.add_activity(f"Publicando paquete {package_id}…", kind="publish")

    try:
        path = resolve_package_path(package_id)
        workflow = MotivacionWorkflow()
        results = workflow.publish_package(str(path), platforms)

        ok = sum(1 for r in results if r.get("success"))
        state.add_activity(
            f"Publicación completada: {ok}/{len(results)} plataformas",
            kind="success" if ok else "warning",
            meta={"results": results},
        )
    except Exception as exc:
        logger.exception("Error en publicación")
        state.add_activity(f"Error al publicar: {exc}", kind="error")
    finally:
        state.set_publish_running(package_id, False)
