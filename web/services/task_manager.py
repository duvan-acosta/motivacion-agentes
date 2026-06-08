"""Estado en memoria de tareas y agentes en ejecución."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentRun:
    agent_id: str
    status: str = "idle"
    theme: str | None = None
    last_run: str | None = None
    last_error: str | None = None
    last_result: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackgroundTask:
    task_id: str
    task_type: str
    status: str
    started_at: str
    finished_at: str | None = None
    message: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TaskManager:
    _instance: TaskManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._agents: dict[str, AgentRun] = {}
        self._tasks: dict[str, BackgroundTask] = {}
        self._activity: list[dict[str, Any]] = []
        self._demo_mode_override: bool | None = None
        self._init_agents()

    @classmethod
    def get(cls) -> TaskManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _init_agents(self) -> None:
        for agent_id in (
            "director",
            "content_creator",
            "visual_designer",
            "video_producer",
            "publisher",
        ):
            self._agents[agent_id] = AgentRun(agent_id=agent_id)

    def set_agent_status(
        self,
        agent_id: str,
        status: str,
        theme: str | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        run = self._agents.setdefault(agent_id, AgentRun(agent_id=agent_id))
        run.status = status
        if theme:
            run.theme = theme
        if error:
            run.last_error = error
        if result:
            run.last_result = result
        if status in ("idle", "error"):
            run.last_run = datetime.now().isoformat()

    def set_all_agents(self, status: str, theme: str | None = None) -> None:
        for agent_id in self._agents:
            self.set_agent_status(agent_id, status, theme=theme)

    def add_activity(self, message: str, level: str = "info", meta: dict | None = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level,
            "meta": meta or {},
        }
        self._activity.insert(0, entry)
        self._activity = self._activity[:50]

    def create_task(self, task_type: str) -> BackgroundTask:
        task_id = f"{task_type}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        task = BackgroundTask(
            task_id=task_id,
            task_type=task_type,
            status="running",
            started_at=datetime.now().isoformat(),
        )
        self._tasks[task_id] = task
        return task

    def complete_task(
        self,
        task: BackgroundTask,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        task.finished_at = datetime.now().isoformat()
        if error:
            task.status = "error"
            task.error = error
            task.message = error
        else:
            task.status = "completed"
            task.result = result or {}
            task.message = "Completado correctamente"
        self._tasks[task.task_id] = task

    def get_tasks(self, limit: int = 20) -> list[BackgroundTask]:
        return sorted(
            self._tasks.values(),
            key=lambda t: t.started_at,
            reverse=True,
        )[:limit]

    def get_agents(self) -> list[AgentRun]:
        return list(self._agents.values())

    def get_activity(self, limit: int = 15) -> list[dict[str, Any]]:
        return self._activity[:limit]

    @property
    def demo_mode_override(self) -> bool | None:
        return self._demo_mode_override

    def set_demo_mode(self, enabled: bool) -> None:
        self._demo_mode_override = enabled
