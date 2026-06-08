#!/usr/bin/env python3
"""CLI principal: generate | publish | status | schedule."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from graph.workflow import MotivacionWorkflow, run_generation
from scheduler.jobs import start_scheduler
from utils.config import get_settings

console = Console()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@click.group()
def cli() -> None:
    """Sistema multi-agente de contenido motivacional en español."""


@cli.command()
@click.option("--theme", "-t", default=None, help="Tema específico (resiliencia, calma, etc.)")
@click.option("--demo", is_flag=True, help="Forzar modo demo sin APIs")
def generate(theme: str | None, demo: bool) -> None:
    """Genera contenido completo (mensaje → imágenes → video → paquete)."""
    settings = get_settings()
    if demo:
        import os

        os.environ["DEMO_MODE"] = "true"
        get_settings.cache_clear()
        settings = get_settings()

    console.print("[bold green]Iniciando generación...[/bold green]")
    if settings.demo_mode or demo:
        console.print("[yellow]Modo demo activo — sin llamadas a APIs externas[/yellow]")

    result = run_generation(theme)
    package = result.get("package_path", "")
    console.print(f"\n[bold]Paquete generado:[/bold] {package}")
    console.print(f"Tema: {result.get('theme')}")
    console.print(f"Mensaje: {result.get('message')}")
    if result.get("errors"):
        console.print(f"[red]Errores: {result['errors']}[/red]")


@cli.command()
@click.argument("package_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--platform",
    "-p",
    multiple=True,
    type=click.Choice(["instagram", "facebook", "tiktok", "youtube", "twitter"]),
    help="Plataforma(s) a publicar",
)
def publish(package_path: Path, platform: tuple[str, ...]) -> None:
    """Publica un paquete existente vía API (con fallback manual)."""
    workflow = MotivacionWorkflow()
    platforms = list(platform) if platform else None
    results = workflow.publish_package(str(package_path), platforms)

    table = Table(title="Resultados de publicación")
    table.add_column("Plataforma")
    table.add_column("Éxito")
    table.add_column("Manual")
    table.add_column("Mensaje")

    for r in results:
        table.add_row(
            r["platform"],
            "✓" if r["success"] else "✗",
            "Sí" if r.get("manual") else "No",
            r["message"][:60],
        )
    console.print(table)


@cli.command()
@click.option("--queue-dir", default=None, help="Directorio publication_queue")
def status(queue_dir: str | None) -> None:
    """Muestra estado de paquetes en publication_queue."""
    settings = get_settings()
    base = Path(queue_dir) if queue_dir else settings.queue_path

    if not base.exists():
        console.print(f"[yellow]No existe {base}[/yellow]")
        return

    table = Table(title=f"Estado — {base}")
    table.add_column("Fecha")
    table.add_column("Contenido")
    table.add_column("Estado")
    table.add_column("Tema")

    count = 0
    for date_dir in sorted(base.iterdir()):
        if not date_dir.is_dir():
            continue
        for pkg in sorted(date_dir.iterdir()):
            if not pkg.is_dir():
                continue
            status_file = pkg / "status.json"
            meta_file = pkg / "source" / "metadata.json"
            st = "unknown"
            theme = "-"
            if status_file.exists():
                st = json.loads(status_file.read_text(encoding="utf-8")).get("status", "unknown")
            if meta_file.exists():
                theme = json.loads(meta_file.read_text(encoding="utf-8")).get("theme", "-")
            table.add_row(date_dir.name, pkg.name, st, theme)
            count += 1

    if count == 0:
        console.print("[dim]Sin paquetes generados aún. Ejecuta: python -m cli generate --demo[/dim]")
    else:
        console.print(table)


@cli.command()
def schedule() -> None:
    """Inicia scheduler APScheduler para generación diaria."""
    settings = get_settings()
    console.print(
        f"[bold]Scheduler — generación diaria a las "
        f"{settings.schedule_hour:02d}:{settings.schedule_minute:02d} "
        f"({settings.timezone})[/bold]"
    )
    console.print("Presiona Ctrl+C para detener.")
    try:
        start_scheduler()
    except KeyboardInterrupt:
        console.print("\nScheduler detenido.")


if __name__ == "__main__":
    cli()
