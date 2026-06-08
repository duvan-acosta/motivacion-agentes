"""Servicio de agentes — metadatos y ejecución de workflows."""

from __future__ import annotations

import os
from typing import Any

from graph.workflow import MotivacionWorkflow, run_generation
from utils.config import get_settings

from web.services.task_manager import TaskManager

AGENT_DEFINITIONS = [
    {
        "id": "director",
        "name": "DirectorAgent",
        "label": "Director",
        "description": "Orquesta temas, calendario editorial y flujo de contenido.",
        "rag_collections": [],
        "workflow_step": "director",
    },
    {
        "id": "content_creator",
        "name": "ContentCreatorAgent",
        "label": "Creador de Contenido",
        "description": "Genera mensaje, caption y hashtags en español con tono filosófico.",
        "rag_collections": ["filosofia", "brand"],
        "workflow_step": "content",
    },
    {
        "id": "visual_designer",
        "name": "VisualDesignerAgent",
        "label": "Diseñador Visual",
        "description": "Define fondo, tipografía y composición visual por tema.",
        "rag_collections": ["visual", "brand"],
        "workflow_step": "visual",
    },
    {
        "id": "video_producer",
        "name": "VideoProducerAgent",
        "label": "Productor de Video",
        "description": "Expande el mensaje en guion de voz, TTS y especificaciones de video.",
        "rag_collections": ["filosofia", "brand"],
        "workflow_step": "video_script",
    },
    {
        "id": "publisher",
        "name": "PublisherAgent",
        "label": "Publicador",
        "description": "Empaqueta assets por plataforma y genera manifest/status.",
        "rag_collections": ["platforms", "brand"],
        "workflow_step": "package",
    },
]

RAG_FILES = {
    "filosofia": "filosofia-es.md",
    "visual": "temas-visuales.md",
    "brand": "brand-voice.md",
    "platforms": "platforms-specs.yaml",
}


def _apply_demo_mode(demo: bool) -> None:
    if demo:
        os.environ["DEMO_MODE"] = "true"
    else:
        os.environ.pop("DEMO_MODE", None)
    get_settings.cache_clear()


def is_demo_mode() -> bool:
    tm = TaskManager.get()
    if tm.demo_mode_override is not None:
        return tm.demo_mode_override
    return get_settings().demo_mode


def set_demo_mode(enabled: bool) -> dict[str, Any]:
    tm = TaskManager.get()
    tm.set_demo_mode(enabled)
    _apply_demo_mode(enabled)
    tm.add_activity(
        f"Modo {'demo' if enabled else 'producción'} activado",
        level="info",
    )
    return {"demo_mode": enabled}


def get_agents_info() -> list[dict[str, Any]]:
    tm = TaskManager.get()
    runs = {r.agent_id: r for r in tm.get_agents()}
    result = []
    for agent in AGENT_DEFINITIONS:
        run = runs.get(agent["id"])
        rag = [
            {"collection": c, "file": RAG_FILES.get(c, "")}
            for c in agent["rag_collections"]
        ]
        result.append(
            {
                **agent,
                "status": run.status if run else "idle",
                "last_run": run.last_run if run else None,
                "theme": run.theme if run else None,
                "last_error": run.last_error if run else None,
            }
        )
    return result


def run_generate_task(theme: str | None = None, demo: bool | None = None) -> dict[str, Any]:
    tm = TaskManager.get()
    use_demo = demo if demo is not None else is_demo_mode()
    _apply_demo_mode(use_demo)

    task = tm.create_task("generate")
    tm.add_activity(
        f"Iniciando generación{' (demo)' if use_demo else ''}"
        + (f" — tema: {theme}" if theme else ""),
        level="info",
    )

    try:
        tm.set_all_agents("running", theme=theme)
        result = run_generation(theme)
        tm.set_all_agents("idle", theme=result.get("theme"))
        tm.complete_task(task, result=result)
        tm.add_activity(
            f"Paquete generado: {result.get('package_path', 'N/A')}",
            level="success",
            meta={"theme": result.get("theme")},
        )
        return {"task_id": task.task_id, "status": "completed", "result": result}
    except Exception as exc:
        for agent_id in tm._agents:
            tm.set_agent_status(agent_id, "error", theme=theme, error=str(exc))
        tm.complete_task(task, error=str(exc))
        tm.add_activity(f"Error en generación: {exc}", level="error")
        raise


def run_publish_task(package_path: str, platforms: list[str] | None = None) -> dict[str, Any]:
    tm = TaskManager.get()
    task = tm.create_task("publish")
    tm.set_agent_status("publisher", "running")
    tm.add_activity(f"Publicando paquete: {package_path}", level="info")

    try:
        workflow = MotivacionWorkflow()
        results = workflow.publish_package(package_path, platforms)
        tm.set_agent_status("publisher", "idle", result={"results": results})
        tm.complete_task(task, result={"results": results})
        tm.add_activity("Publicación completada", level="success")
        return {"task_id": task.task_id, "status": "completed", "results": results}
    except Exception as exc:
        tm.set_agent_status("publisher", "error", error=str(exc))
        tm.complete_task(task, error=str(exc))
        tm.add_activity(f"Error en publicación: {exc}", level="error")
        raise
