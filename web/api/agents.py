"""Router de agentes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from web.services import agent_service, state

router = APIRouter(prefix="/api/agents", tags=["agents"])


class GenerateRequest(BaseModel):
    theme: str | None = None
    demo: bool | None = None


class DemoModeRequest(BaseModel):
    enabled: bool


@router.get("")
def get_agents():
    return {
        "agents": agent_service.list_agents(),
        "demo_mode": state.get_demo_mode(),
        "generation_running": state.is_generation_running(),
        "last_run": state.get_last_run(),
    }


@router.post("/generate")
def trigger_generate(body: GenerateRequest, background_tasks: BackgroundTasks):
    if state.is_generation_running():
        return {"ok": False, "message": "Ya hay una generación en curso"}

    background_tasks.add_task(agent_service.run_generation_task, body.theme, body.demo)
    return {
        "ok": True,
        "message": "Generación iniciada en segundo plano",
        "theme": body.theme,
        "demo": body.demo if body.demo is not None else state.get_demo_mode(),
    }


@router.post("/workflow")
def trigger_workflow(body: GenerateRequest, background_tasks: BackgroundTasks):
    if state.is_generation_running():
        return {"ok": False, "message": "Ya hay un workflow en curso"}

    background_tasks.add_task(agent_service.run_full_workflow_task, body.theme, body.demo)
    return {
        "ok": True,
        "message": "Workflow completo iniciado en segundo plano",
    }


@router.post("/demo-mode")
def set_demo_mode(body: DemoModeRequest):
    state.set_demo_mode(body.enabled)
    return {"ok": True, "demo_mode": state.get_demo_mode()}
