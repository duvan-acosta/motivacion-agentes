"""Aplicación FastAPI del panel de administración."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web.api import agents, analytics, content, dashboard, services

WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Motivación Agentes — Panel Admin",
    description="Panel web para administrar agentes, servicios y contenido generado",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(services.router)
app.include_router(content.router)
app.include_router(analytics.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
