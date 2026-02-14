from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.scheduler import TaskQueue
from app.core.db import db
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Tuple
import uuid
import asyncio

class ScheduledJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    cron_expression: str # Standard string like "0 9 * * *" or specific fields
    task_prompt: str # The task to add to the queue when triggered
    enabled: bool = True

class CronManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CronManager, cls).__new__(cls)
            cls._instance.scheduler = AsyncIOScheduler()
            cls._instance.queue = TaskQueue()
            cls._instance.jobs = {} # In-memory cache
            cls._instance._load_jobs()
        return cls._instance

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            print(">>> Cron Scheduler Started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            print(">>> Cron Scheduler Stopped")

    def _load_jobs(self):
        try:
            rows = db.get_jobs()
            loaded_jobs = [ScheduledJob(**row) for row in rows]

            # Deduplicate logical duplicates left from prior runs/migrations.
            # We consider same name + cron expression to be one scheduled job.
            seen_fingerprints: Dict[str, str] = {}
            for job in loaded_jobs:
                fingerprint = self._job_fingerprint(job.name, job.cron_expression)
                if fingerprint in seen_fingerprints:
                    db.remove_job(job.id)
                    print(
                        f"Removed duplicate cron job '{job.name}' ({job.id}); "
                        f"keeping {seen_fingerprints[fingerprint]}"
                    )
                    continue

                seen_fingerprints[fingerprint] = job.id
                self.jobs[job.id] = job
                self._schedule_internal(job)
                
        except Exception as e:
            print(f"Error loading cron jobs: {e}")

    def _job_fingerprint(self, name: str, cron_expression: str) -> str:
        normalized_cron = " ".join(cron_expression.split())
        return f"{name.strip()}||{normalized_cron}"

    def _schedule_internal(self, job: ScheduledJob):
        # Determine trigger method
        # We'll support standard 5-part cron strings: "minute hour day month day_of_week"
        # e.g. "*/5 * * * *" -> Every 5 minutes
        
        try:
            if not job.enabled:
                return

            parts = job.cron_expression.split()
            if len(parts) != 5:
                print(f"Invalid cron format for job {job.name}: {job.cron_expression}")
                return

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )

            job_id = f"cron_{job.id}"
            
            # Remove functionality if exists to update it
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)

            self.scheduler.add_job(
                self._execute_job,
                trigger,
                args=[job],
                id=job_id,
                name=job.name
            )
            print(f"Scheduled job '{job.name}' with cron: {job.cron_expression}")
            
        except Exception as e:
            print(f"Failed to schedule job {job.name}: {e}")

    async def _execute_job(self, job: ScheduledJob):
        print(f">>> CRON EXECUTION: {job.name}")
        status, task_id = self._enqueue_job_task(job)
        if status == "skipped_active":
            print(f"    Skipped enqueue for '{job.name}' (active task already exists).")
            return
        print(f"    Added task {task_id} to queue.")

    def _enqueue_job_task(self, job: ScheduledJob) -> Tuple[str, Optional[str]]:
        task_title = f"[Scheduled] {job.name}"

        # Coalesce active queue entries so one logical cron job does not flood duplicates.
        if self.queue.has_active_task(task_title, job.task_prompt):
            return "skipped_active", None

        # Add a task to the queue with high priority
        new_task = self.queue.add_task(
            title=task_title,
            description=job.task_prompt,
            priority=4
        )
        return "enqueued", new_task.id

    def run_job_now(self, job_id: str) -> Tuple[str, Optional[str]]:
        job = self.jobs.get(job_id)
        if not job:
            return "not_found", None
        return self._enqueue_job_task(job)

    def add_job(self, name: str, cron_expression: str, task_prompt: str) -> str:
        fingerprint = self._job_fingerprint(name, cron_expression)
        for existing in self.jobs.values():
            if self._job_fingerprint(existing.name, existing.cron_expression) == fingerprint:
                # Idempotent behavior: don't create duplicate logical jobs.
                return existing.id

        job = ScheduledJob(
            name=name,
            cron_expression=cron_expression,
            task_prompt=task_prompt
        )
        self.jobs[job.id] = job
        self._schedule_internal(job)
        db.add_job(job.model_dump())
        return job.id

    def remove_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            # Remove from scheduler
            scheduler_job_id = f"cron_{job_id}"
            if self.scheduler.get_job(scheduler_job_id):
                self.scheduler.remove_job(scheduler_job_id)
            
            db.remove_job(job_id)
            return True
        return False

    def update_job(
        self,
        job_id: str,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        task_prompt: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[ScheduledJob]:
        existing = self.jobs.get(job_id)
        if not existing:
            return None

        updated = ScheduledJob(
            id=existing.id,
            name=name if name is not None else existing.name,
            cron_expression=cron_expression if cron_expression is not None else existing.cron_expression,
            task_prompt=task_prompt if task_prompt is not None else existing.task_prompt,
            enabled=enabled if enabled is not None else existing.enabled,
        )

        new_fingerprint = self._job_fingerprint(updated.name, updated.cron_expression)
        for other in self.jobs.values():
            if other.id == job_id:
                continue
            other_fingerprint = self._job_fingerprint(other.name, other.cron_expression)
            if other_fingerprint == new_fingerprint:
                raise ValueError(
                    "A scheduled cron job with the same name and cron expression already exists."
                )

        # Ensure scheduler state reflects new config.
        scheduler_job_id = f"cron_{job_id}"
        if self.scheduler.get_job(scheduler_job_id):
            self.scheduler.remove_job(scheduler_job_id)

        self.jobs[job_id] = updated
        self._schedule_internal(updated)
        db.update_job(job_id, updated.model_dump(exclude={"id"}))
        return updated

    def list_jobs(self) -> List[ScheduledJob]:
        return list(self.jobs.values())

cron_manager = CronManager()
