import asyncio
import logging
import time
from app.core.scheduler import TaskQueue, AgentTask

logger = logging.getLogger(__name__)

STALE_IN_PROGRESS_TIMEOUT_SECONDS = 3600  # 1 hour
MAX_PARALLEL_READY_TASKS = 3


class AgentHeartbeat:
    def __init__(self, interval: int = 1800):
        self.interval = interval
        self.running = False
        self.queue = TaskQueue()
        self.last_tick_at = 0.0
        self.next_tick_at = 0.0

    async def start(self):
        self.running = True
        logger.info(">>> Agent Heartbeat Started (interval=%ss)", self.interval)
        while self.running:
            try:
                self.last_tick_at = time.time()
                logger.info("Heartbeat: Tick started")
                await self.tick()
                logger.info("Heartbeat: Tick completed")
            except Exception as e:
                logger.error(f"Error in heartbeat tick: {e}", exc_info=True)

            self.next_tick_at = time.time() + self.interval
            await asyncio.sleep(self.interval)

    async def stop(self):
        self.running = False
        self.next_tick_at = 0.0
        logger.info(">>> Agent Heartbeat Stopped")

    def get_runtime_status(self) -> dict:
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "last_tick_at": self.last_tick_at,
            "next_tick_at": self.next_tick_at,
        }

    async def tick(self):
        # Reconcile stale executions that may have been left in-progress by prior crashes/restarts.
        stale_count = self.queue.reconcile_stale_in_progress(STALE_IN_PROGRESS_TIMEOUT_SECONDS)
        if stale_count:
            logger.warning(
                "Heartbeat: Marked %s stale in-progress task(s) as failed",
                stale_count,
            )

        deduped_count = self.queue.reconcile_duplicate_scheduled_active()
        if deduped_count:
            logger.warning(
                "Heartbeat: Coalesced %s duplicate active scheduled task(s)",
                deduped_count,
            )

        # 1. Check for Pending Tasks (Reactive)
        ready_tasks = self.queue.list_ready_pending(limit=MAX_PARALLEL_READY_TASKS)
        if ready_tasks:
            parallel_ready = [t for t in ready_tasks if self.queue.allows_parallel(t)]
            if len(parallel_ready) >= 2:
                logger.info(
                    "Heartbeat: %s parallel-ready task(s) detected",
                    len(parallel_ready),
                )
                await asyncio.gather(*(self.process_task(t) for t in parallel_ready))
            else:
                task = ready_tasks[0]
                logger.info("Heartbeat: Reactive task detected (id=%s, title=%s)", task.id, task.title)
                await self.process_task(task)
            return

        # Only invoke the model when there is queued work.
        logger.info("Heartbeat: No ready pending tasks; skipping model invocation")

    async def process_task(self, task: AgentTask):
        # Fresh orchestrator per task to avoid shared mutable runtime state across parallel executions.
        from app.agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()

        logger.info(f"Heartbeat: Picked up task '{task.title}'")

        # Mark as In Progress
        self.queue.update_task_status(task.id, "in_progress")

        try:
            # Check if orchestrator.run supports session
            from app.agents.session_manager import SessionManager

            sm = SessionManager()
            session_id = f"task_{task.id}"
            session = await sm.load_session(session_id)

            # Construct a prompt for the agent
            prompt = (
                f"Background Task Execution:\nTitle: {task.title}\nDescription: {self.queue.get_task_prompt_description(task)}\n\n"
                "Please execute this task. Use available tools if necessary."
            )

            response = await orchestrator.run(
                prompt,
                session,
                source_channel="heartbeat",
                source_metadata={"transport": "scheduler"},
            )

            if response.session_data:
                await sm.save_session(response.session_data)

            # Mark Complete
            result_summary = response.response
            if response.metadata.get("tools_used"):
                result_summary += f"\n[Tools Used: {', '.join(response.metadata['tools_used'])}]"

            self.queue.update_task_status(task.id, "completed", result=result_summary)
            logger.info(f"Heartbeat: Task '{task.title}' completed.")

        except Exception as e:
            logger.error(f"Heartbeat: Task '{task.title}' failed: {e}")
            self.queue.update_task_status(task.id, "failed", result=str(e))
