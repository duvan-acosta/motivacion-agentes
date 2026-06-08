"""Router de material generado."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from utils.config import get_settings
from web.services import agent_service, content_service, state

router = APIRouter(prefix="/api/content", tags=["content"])


class PublishRequest(BaseModel):
    platforms: list[str] | None = None


@router.get("/packages")
def list_packages(limit: int = Query(default=50, le=200)):
    return {"packages": content_service.list_packages(limit=limit)}


@router.get("/packages/{package_id:path}")
def get_package(package_id: str):
    try:
        return content_service.get_package_detail(package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/packages/{package_id:path}/publish")
def publish_package(
    package_id: str,
    body: PublishRequest,
    background_tasks: BackgroundTasks,
):
    if state.is_publish_running(package_id):
        return {"ok": False, "message": "Publicación ya en curso para este paquete"}

    try:
        content_service.resolve_package_path(package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(agent_service.run_publish_task, package_id, body.platforms)
    return {"ok": True, "message": "Publicación iniciada en segundo plano"}


@router.get("/packages/{package_id:path}/download")
def download_package(package_id: str):
    try:
        filename, buffer = content_service.create_package_zip(package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/media/{file_path:path}")
def serve_media(file_path: str):
    root = get_settings().project_root
    full = (root / file_path).resolve()
    if not str(full).startswith(str(root.resolve())):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(full)
