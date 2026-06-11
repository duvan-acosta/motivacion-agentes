"""Scheduler APScheduler para ejecución diaria."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from graph.workflow import MotivacionWorkflow
from utils.config import get_settings

logger = logging.getLogger(__name__)


def daily_generation_job() -> None:
    logger.info("Ejecutando generación diaria programada")
    settings = get_settings()
    workflow = MotivacionWorkflow()
    result = workflow.run()
    package_path = result.get("package_path")
    logger.info("Generación completada: %s", package_path or "sin paquete")

    # Auto-publicación opcional (AUTO_PUBLISH_PLATFORMS). Vacío = solo genera.
    platforms = settings.auto_publish_list()
    if package_path and platforms:
        logger.info("Auto-publicando en: %s", ", ".join(platforms))
        for r in workflow.publish_package(package_path, platforms):
            estado = "ok" if r.get("success") else r.get("message", "fallo")
            logger.info("  %s → %s", r.get("platform"), estado)


def start_scheduler() -> None:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=settings.timezone)
    trigger = CronTrigger(
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        timezone=settings.timezone,
    )
    scheduler.add_job(daily_generation_job, trigger, id="daily_generation", replace_existing=True)
    logger.info(
        "Scheduler iniciado — generación diaria a las %02d:%02d (%s)",
        settings.schedule_hour,
        settings.schedule_minute,
        settings.timezone,
    )
    scheduler.start()
