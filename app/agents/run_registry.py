"""
Active Run Registry — tracks, steers, and aborts live agent runs.

Every orchestrator loop iteration should check `run.abort_event.is_set()`
and drain `run.steer_queue` between tool calls.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

RunStatus = Literal["running", "completed", "aborted", "timed_out"]


@dataclass
class RunHandle:
    """Represents a single active agent run."""

    session_id: str
    abort_event: asyncio.Event = field(default=None)
    steer_queue: asyncio.Queue = field(default=None)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: RunStatus = "running"
    current_turn: int = 0
    max_turns: int = 25
    cancel_reason: Optional[str] = None
    _done_event: asyncio.Event = field(default=None, repr=False)
    _timeout_task: Optional[asyncio.Task[None]] = field(default=None, repr=False)

    def __post_init__(self):
        """Lazily create asyncio primitives so they bind to the running loop."""
        if self.abort_event is None:
            self.abort_event = asyncio.Event()
        if self.steer_queue is None:
            self.steer_queue = asyncio.Queue()
        if self._done_event is None:
            self._done_event = asyncio.Event()


# ── Module-level registry ────────────────────────────────────────────
ACTIVE_RUNS: Dict[str, RunHandle] = {}


# ── Helpers ───────────────────────────────────────────────────────────

async def _auto_abort(session_id: str, timeout_ms: int) -> None:
    """Background task that aborts a run after *timeout_ms* milliseconds."""
    try:
        await asyncio.sleep(timeout_ms / 1000.0)
    except asyncio.CancelledError:
        return
    run = ACTIVE_RUNS.get(session_id)
    if run and run.status == "running":
        run.status = "timed_out"
        run.cancel_reason = f"timeout_{timeout_ms}ms"
        run.abort_event.set()
        run._done_event.set()
        logger.warning("Run %s auto-aborted after %dms timeout", session_id, timeout_ms)


# ── Public API ────────────────────────────────────────────────────────

def register_run(
    session_id: str,
    max_turns: int = 25,
    timeout_ms: int = 0,
) -> RunHandle:
    """Create and register a new run.

    Args:
        session_id: Unique identifier for this run.
        max_turns: Maximum orchestrator turns before auto-stop.
        timeout_ms: Wall-clock timeout in milliseconds.  0 = no timeout.

    Returns:
        The newly created ``RunHandle``.

    Raises:
        ValueError: If a run with *session_id* is already active.
    """
    if session_id in ACTIVE_RUNS:
        raise ValueError(f"Run {session_id!r} is already active")

    handle = RunHandle(session_id=session_id, max_turns=max_turns)

    if timeout_ms > 0:
        handle._timeout_task = asyncio.get_event_loop().create_task(
            _auto_abort(session_id, timeout_ms),
            name=f"run-timeout-{session_id}",
        )

    ACTIVE_RUNS[session_id] = handle
    logger.info(
        "Registered run %s (max_turns=%d, timeout_ms=%d)",
        session_id,
        max_turns,
        timeout_ms,
    )
    return handle


def abort_run(session_id: str, reason: str = "user_cancelled") -> bool:
    """Abort an active run.

    Sets the abort event so the orchestrator loop stops at the next
    check-point and marks the run as *aborted*.

    Returns:
        ``True`` if the run was found and aborted, ``False`` otherwise.
    """
    run = ACTIVE_RUNS.get(session_id)
    if run is None or run.status != "running":
        logger.debug("abort_run called for non-active session %s", session_id)
        return False

    run.status = "aborted"
    run.cancel_reason = reason
    run.abort_event.set()
    run._done_event.set()

    if run._timeout_task and not run._timeout_task.done():
        run._timeout_task.cancel()

    logger.info("Aborted run %s (reason=%s)", session_id, reason)
    return True


def get_run_status(session_id: str) -> Optional[RunHandle]:
    """Return the ``RunHandle`` for *session_id*, or ``None``."""
    return ACTIVE_RUNS.get(session_id)


def complete_run(session_id: str) -> None:
    """Mark a run as completed and remove it from the active registry."""
    run = ACTIVE_RUNS.pop(session_id, None)
    if run is None:
        logger.debug("complete_run called for unknown session %s", session_id)
        return

    run.status = "completed"
    run._done_event.set()

    if run._timeout_task and not run._timeout_task.done():
        run._timeout_task.cancel()

    logger.info(
        "Completed run %s after %d turns (%.1fs)",
        session_id,
        run.current_turn,
        (datetime.now(timezone.utc) - run.started_at).total_seconds(),
    )


async def wait_for_run_end(session_id: str, timeout_seconds: float = 0) -> bool:
    """Block until a run finishes (completed, aborted, or timed-out).

    Args:
        session_id: The run to wait on.
        timeout_seconds: Max seconds to wait.  0 = wait indefinitely.

    Returns:
        ``True`` if the run ended within the timeout, ``False`` on timeout
        or if the session was not found.
    """
    run = ACTIVE_RUNS.get(session_id)
    if run is None:
        return False

    try:
        if timeout_seconds > 0:
            await asyncio.wait_for(run._done_event.wait(), timeout=timeout_seconds)
        else:
            await run._done_event.wait()
        return True
    except asyncio.TimeoutError:
        return False


def list_active_runs() -> List[RunHandle]:
    """Return a snapshot of all currently active runs."""
    return list(ACTIVE_RUNS.values())


def update_run_turn(session_id: str, turn_num: int) -> None:
    """Update the current turn counter for a run.

    If *turn_num* reaches ``max_turns``, the run is automatically aborted
    with reason ``max_turns_reached``.
    """
    run = ACTIVE_RUNS.get(session_id)
    if run is None:
        return

    run.current_turn = turn_num

    if run.max_turns and turn_num > run.max_turns:
        run.status = "aborted"
        run.cancel_reason = "max_turns_reached"
        run.abort_event.set()
        run._done_event.set()
        logger.warning(
            "Run %s hit max turns (%d/%d) — auto-aborting",
            session_id,
            turn_num,
            run.max_turns,
        )
