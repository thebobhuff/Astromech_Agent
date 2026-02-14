from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime, timedelta
import uuid
import json
from app.core.db import db
from app.memory.rag import get_vector_memory

PLAN_META_BEGIN = "[[PLAN_META]]"
PLAN_META_END = "[[/PLAN_META]]"


def encode_plan_description(description: str, meta: dict) -> str:
    return f"{PLAN_META_BEGIN}{json.dumps(meta, ensure_ascii=True)}{PLAN_META_END}\n{description or ''}".strip()


def decode_plan_description(description: Optional[str]) -> tuple[dict, str]:
    text = description or ""
    if not text.startswith(PLAN_META_BEGIN):
        return {}, text
    end_idx = text.find(PLAN_META_END)
    if end_idx == -1:
        return {}, text
    payload = text[len(PLAN_META_BEGIN):end_idx]
    remainder = text[end_idx + len(PLAN_META_END):].lstrip("\r\n")
    try:
        return json.loads(payload), remainder
    except Exception:
        return {}, text


class AgentTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    priority: int = 1 # 1 (Low) to 5 (Urgent)
    result: Optional[str] = None

class TaskQueue:
    def __init__(self):
        pass # DB is initialized globally

    def load_tasks(self) -> List[AgentTask]:
        """Loads all tasks from the DB."""
        rows = db.get_tasks()
        tasks = [AgentTask(**row) for row in rows]
        return [self.to_public_task(t) for t in tasks]

    def add_task(self, title: str, description: str = "", priority: int = 3) -> AgentTask:
        new_task = AgentTask(title=title, description=description, priority=priority)
        db.add_task(new_task.model_dump())
        return new_task

    def get_next_pending(self) -> Optional[AgentTask]:
        """Fetches the next highest priority pending task that has dependencies satisfied."""
        rows = db.get_tasks(status="pending")
        if not rows:
            return None
        pending_tasks = [AgentTask(**row) for row in rows]
        completed_rows = db.get_tasks(status="completed")
        completed_tasks = [AgentTask(**row) for row in completed_rows]
        completed_step_ids = self._completed_plan_step_ids(completed_tasks)

        for task in pending_tasks:
            if self._dependencies_satisfied(task, completed_step_ids):
                return task
        return None

    def list_pending(self, limit: int = 10) -> List[AgentTask]:
        rows = db.get_tasks(status="pending")
        tasks = [AgentTask(**row) for row in rows[: max(0, limit)]]
        return [self.to_public_task(t) for t in tasks]

    def list_ready_pending(self, limit: int = 10) -> List[AgentTask]:
        rows = db.get_tasks(status="pending")
        if not rows:
            return []
        pending_tasks = [AgentTask(**row) for row in rows]
        completed_rows = db.get_tasks(status="completed")
        completed_tasks = [AgentTask(**row) for row in completed_rows]
        completed_step_ids = self._completed_plan_step_ids(completed_tasks)
        ready = [t for t in pending_tasks if self._dependencies_satisfied(t, completed_step_ids)]
        return ready[: max(0, limit)]

    def has_active_task(self, title: str, description: Optional[str] = None) -> bool:
        active_statuses = {"pending", "in_progress"}
        for row in db.get_tasks():
            task = AgentTask(**row)
            if task.status not in active_statuses:
                continue
            if task.title != title:
                continue
            if description is not None and (task.description or "") != description:
                continue
            return True
        return False

    def update_task_status(self, task_id: str, status: str, result: str = None):
        updated_at = datetime.now().isoformat()
        db.update_task_status(task_id, status, result, updated_at)

    def reconcile_stale_in_progress(self, max_age_seconds: int = 3600) -> int:
        """Mark stale in-progress tasks as failed so they can exit the active queue."""
        stale_before = datetime.now() - timedelta(seconds=max(1, max_age_seconds))
        scheduled_stale_before = datetime.now() - timedelta(seconds=min(max(1, max_age_seconds), 900))
        stale_count = 0

        for row in db.get_tasks(status="in_progress"):
            task = AgentTask(**row)
            try:
                updated_at = datetime.fromisoformat(task.updated_at)
            except Exception:
                updated_at = datetime.now()

            is_scheduled = task.title.startswith("[Scheduled] ")
            cutoff = scheduled_stale_before if is_scheduled else stale_before

            if updated_at <= cutoff:
                stale_count += 1
                self.update_task_status(
                    task.id,
                    "failed",
                    result=(
                        "Scheduled task exceeded max in-progress time (900s) and was marked stale."
                        if is_scheduled
                        else f"Task exceeded max in-progress time ({max_age_seconds}s) and was marked stale."
                    ),
                )

        return stale_count

    def reconcile_duplicate_scheduled_active(self) -> int:
        """Collapse duplicate active scheduled tasks, keeping only one active task per logical job."""
        active_statuses = {"pending", "in_progress"}
        groups: dict[tuple[str, str], List[AgentTask]] = {}

        for row in db.get_tasks():
            task = AgentTask(**row)
            if task.status not in active_statuses:
                continue
            if not task.title.startswith("[Scheduled] "):
                continue
            key = (task.title, task.description or "")
            groups.setdefault(key, []).append(task)

        deduped = 0
        for _, tasks in groups.items():
            if len(tasks) <= 1:
                continue

            # Keep currently running task if present; otherwise keep the oldest queued task.
            in_progress = [t for t in tasks if t.status == "in_progress"]
            if in_progress:
                keep_id = sorted(in_progress, key=lambda t: t.updated_at)[0].id
            else:
                keep_id = sorted(tasks, key=lambda t: t.created_at)[0].id

            for task in tasks:
                if task.id == keep_id:
                    continue
                deduped += 1
                self.update_task_status(
                    task.id,
                    "failed",
                    result="Duplicate scheduled task coalesced; another active run already exists.",
                )

        return deduped

    def to_public_task(self, task: AgentTask) -> AgentTask:
        _, clean_description = decode_plan_description(task.description)
        return task.model_copy(update={"description": clean_description})

    def get_task_prompt_description(self, task: AgentTask) -> str:
        _, clean_description = decode_plan_description(task.description)
        return clean_description

    def allows_parallel(self, task: AgentTask) -> bool:
        meta, _ = decode_plan_description(task.description)
        return bool(meta.get("parallelizable", False))

    def _completed_plan_step_ids(self, completed_tasks: List[AgentTask]) -> set[str]:
        done: set[str] = set()
        for task in completed_tasks:
            meta, _ = decode_plan_description(task.description)
            step_id = meta.get("step_id")
            if step_id:
                done.add(str(step_id))
        return done

    def _dependencies_satisfied(self, task: AgentTask, completed_step_ids: set[str]) -> bool:
        meta, _ = decode_plan_description(task.description)
        deps = meta.get("depends_on", []) if isinstance(meta, dict) else []
        if not isinstance(deps, list):
            return True
        for dep in deps:
            if str(dep) not in completed_step_ids:
                return False
        return True
