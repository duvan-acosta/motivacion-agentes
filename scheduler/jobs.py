"""Scheduler APScheduler — publicación multi-plataforma en horarios óptimos."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from graph.workflow import run_generation
from utils.config import get_settings

logger = logging.getLogger(__name__)

# Horarios óptimos por plataforma (hora local Colombia UTC-5)
# Basados en estudios de engagement LATAM 2024-2025
SCHEDULE = [
    # hora, plataformas objetivo, etiqueta
    (6,  0,  ["instagram", "facebook", "twitter"],         "mañana_ig_fb_x"),
    (7,  0,  ["tiktok", "youtube"],                        "mañana_tt_yt"),
    (12, 0,  ["tiktok", "twitter"],                        "mediodia_tt_x"),
    (13, 0,  ["facebook"],                                 "almuerzo_fb"),
    (19, 0,  ["tiktok", "youtube"],                        "tarde_tt_yt"),
    (20, 0,  ["instagram", "twitter"],                     "noche_ig_x"),
]


def _run_job(platforms: list[str], label: str) -> None:
    settings = get_settings()
    logger.info("[scheduler] Job '%s' — plataformas: %s", label, ", ".join(platforms))

    result = run_generation()
    package_path = result.get("package_path", "")

    if not package_path:
        logger.warning("[scheduler] Job '%s' — sin paquete generado", label)
        return

    logger.info("[scheduler] Paquete listo: %s", package_path)

    if settings.auto_publish_browser:
        from agents.browser_publisher import BrowserPublisherAgent
        agent = BrowserPublisherAgent()
        pub = agent.publish(package_path, platforms=platforms)
        published = pub.get("published", [])
        logger.info("[scheduler] Job '%s' publicado en: %s",
                    label, ", ".join(published) or "ninguna")
    else:
        logger.info("[scheduler] AUTO_PUBLISH_BROWSER=false — paquete listo para publicación manual")


def start_scheduler() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)

    for hour, minute, platforms, label in SCHEDULE:
        trigger = CronTrigger(hour=hour, minute=minute, timezone=settings.timezone)
        # Necesitamos un closure para capturar platforms/label por valor
        def make_job(p: list[str], lbl: str):
            def job():
                _run_job(p, lbl)
            job.__name__ = f"job_{lbl}"
            return job

        scheduler.add_job(
            make_job(platforms, label),
            trigger,
            id=f"job_{label}",
            replace_existing=True,
        )
        logger.info(
            "[scheduler] Registrado: %02d:%02d → %s (%s)",
            hour, minute, ", ".join(platforms), label,
        )

    logger.info(
        "[scheduler] Iniciado — 6 jobs diarios | timezone: %s | AUTO_PUBLISH_BROWSER=%s",
        settings.timezone,
        settings.auto_publish_browser,
    )
    scheduler.start()
