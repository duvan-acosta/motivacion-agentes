"""Scheduler APScheduler para ejecución diaria."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from graph.workflow import run_generation
from utils.config import get_settings

logger = logging.getLogger(__name__)


def daily_generation_job() -> None:
    logger.info("Ejecutando generación diaria programada")
    result = run_generation()
    logger.info("Generación completada: %s", result.get("package_path", "sin paquete"))


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
