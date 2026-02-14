from fastapi import APIRouter, HTTPException
from app.core.scheduler import TaskQueue, AgentTask
from app.core.cron import cron_manager
from pydantic import BaseModel
from typing import List, Optional, Dict

router = APIRouter()
queue = TaskQueue()
STALE_IN_PROGRESS_TIMEOUT_SECONDS = 3600

class AddTaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: int = 3


class TaskHistoryResponse(BaseModel):
    cron_runs: List[AgentTask]
    heartbeat_completed: List[AgentTask]


class ScheduledJobResponse(BaseModel):
    id: str
    name: str
    cron_expression: str
    task_prompt: str
    enabled: bool
    next_run_at: Optional[str] = None


class UpdateCronJobRequest(BaseModel):
    name: str
    cron_expression: str
    task_prompt: str
    enabled: bool = True

@router.get("/")
def list_tasks():
    queue.reconcile_stale_in_progress(STALE_IN_PROGRESS_TIMEOUT_SECONDS)
    queue.reconcile_duplicate_scheduled_active()
    return queue.load_tasks()

@router.post("/")
def add_task(req: AddTaskRequest):
    task = queue.add_task(req.title, req.description, req.priority)
    return task


@router.get("/next-heartbeat-tasks", response_model=List[AgentTask])
def list_next_heartbeat_tasks(limit: int = 10):
    safe_limit = min(max(limit, 1), 50)
    return queue.list_pending(limit=safe_limit)


@router.get("/cron", response_model=List[ScheduledJobResponse])
def list_cron_jobs():
    jobs = cron_manager.list_jobs()
    seen: Dict[str, ScheduledJobResponse] = {}
    response: List[ScheduledJobResponse] = []
    for job in jobs:
        scheduler_job = cron_manager.scheduler.get_job(f"cron_{job.id}")
        next_run = scheduler_job.next_run_time.isoformat() if scheduler_job and scheduler_job.next_run_time else None
        item = ScheduledJobResponse(
            id=job.id,
            name=job.name,
            cron_expression=job.cron_expression,
            task_prompt=job.task_prompt,
            enabled=job.enabled,
            next_run_at=next_run,
        )
        # Defensive dedupe for legacy rows that may have duplicate logical jobs.
        # Logical identity = same name + same cron expression.
        fingerprint = f"{job.name.strip()}||{' '.join(job.cron_expression.split())}"
        if fingerprint not in seen:
            seen[fingerprint] = item
            response.append(item)
    return response


@router.put("/cron/{job_id}", response_model=ScheduledJobResponse)
def update_cron_job(job_id: str, req: UpdateCronJobRequest):
    try:
        updated = cron_manager.update_job(
            job_id=job_id,
            name=req.name,
            cron_expression=req.cron_expression,
            task_prompt=req.task_prompt,
            enabled=req.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    scheduler_job = cron_manager.scheduler.get_job(f"cron_{updated.id}")
    next_run = scheduler_job.next_run_time.isoformat() if scheduler_job and scheduler_job.next_run_time else None
    return ScheduledJobResponse(
        id=updated.id,
        name=updated.name,
        cron_expression=updated.cron_expression,
        task_prompt=updated.task_prompt,
        enabled=updated.enabled,
        next_run_at=next_run,
    )


@router.delete("/cron/{job_id}")
def delete_cron_job(job_id: str):
    if not cron_manager.remove_job(job_id):
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return {"status": "deleted", "job_id": job_id}


@router.post("/cron/{job_id}/run-now")
def run_cron_job_now(job_id: str):
    status, task_id = cron_manager.run_job_now(job_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    if status == "skipped_active":
        return {"status": "skipped_active", "reason": "active_task_exists"}
    return {"status": "enqueued", "task_id": task_id}


@router.get("/history", response_model=TaskHistoryResponse)
def get_task_history():
    completed_tasks = [t for t in queue.load_tasks() if t.status == "completed"]
    cron_runs = [t for t in completed_tasks if t.title.startswith("[Scheduled] ")]
    heartbeat_completed = [t for t in completed_tasks if not t.title.startswith("[Scheduled] ")]
    return TaskHistoryResponse(cron_runs=cron_runs, heartbeat_completed=heartbeat_completed)
