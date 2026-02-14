from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class QueueEntry:
    run_id: str
    session_id: str
    source: str = "api"
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    cancelled: bool = False


@dataclass
class QueueLease:
    entry: QueueEntry
    session_lock: asyncio.Lock


class RunLaneQueue:
    """FIFO run queue with global concurrency + per-session serialization."""

    def __init__(self, max_global_concurrency: int = 2):
        self.max_global_concurrency = max(1, int(max_global_concurrency))
        self._global_semaphore = asyncio.Semaphore(self.max_global_concurrency)
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._pending: List[str] = []
        self._entries: Dict[str, QueueEntry] = {}
        self._active_by_session: Dict[str, str] = {}
        self._cond = asyncio.Condition()

    async def enqueue(self, session_id: str, source: str = "api") -> QueueEntry:
        entry = QueueEntry(run_id=str(uuid.uuid4()), session_id=session_id, source=source)
        async with self._cond:
            self._entries[entry.run_id] = entry
            self._pending.append(entry.run_id)
            self._cond.notify_all()
        return entry

    async def cancel(self, run_id: str) -> bool:
        async with self._cond:
            entry = self._entries.get(run_id)
            if not entry:
                return False
            entry.cancelled = True
            if run_id in self._pending:
                self._pending.remove(run_id)
                self._entries.pop(run_id, None)
            self._cond.notify_all()
            return True

    async def acquire(self, entry: QueueEntry, timeout_seconds: float = 0) -> QueueLease:
        async def _wait_and_acquire() -> QueueLease:
            while True:
                async with self._cond:
                    while True:
                        if entry.cancelled:
                            raise asyncio.CancelledError("Queue entry cancelled")
                        is_head = bool(self._pending) and self._pending[0] == entry.run_id
                        if is_head:
                            break
                        await self._cond.wait()

                await self._global_semaphore.acquire()
                session_lock = self._session_locks.setdefault(entry.session_id, asyncio.Lock())
                await session_lock.acquire()

                async with self._cond:
                    if entry.cancelled:
                        session_lock.release()
                        self._global_semaphore.release()
                        raise asyncio.CancelledError("Queue entry cancelled")

                    is_still_head = bool(self._pending) and self._pending[0] == entry.run_id
                    session_busy = entry.session_id in self._active_by_session
                    if is_still_head and not session_busy:
                        self._pending.pop(0)
                        entry.started_at = datetime.now(timezone.utc)
                        self._active_by_session[entry.session_id] = entry.run_id
                        self._cond.notify_all()
                        return QueueLease(entry=entry, session_lock=session_lock)

                    session_lock.release()
                    self._global_semaphore.release()
                    await asyncio.sleep(0)

        if timeout_seconds and timeout_seconds > 0:
            return await asyncio.wait_for(_wait_and_acquire(), timeout=timeout_seconds)
        return await _wait_and_acquire()

    async def release(self, lease: QueueLease) -> None:
        session_id = lease.entry.session_id
        run_id = lease.entry.run_id
        async with self._cond:
            if self._active_by_session.get(session_id) == run_id:
                self._active_by_session.pop(session_id, None)
            self._entries.pop(run_id, None)
            self._cond.notify_all()
        lease.session_lock.release()
        self._global_semaphore.release()

    async def get_session_queue_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with self._cond:
            active_run_id = self._active_by_session.get(session_id)
            if active_run_id:
                entry = self._entries.get(active_run_id)
                return {
                    "state": "running",
                    "session_id": session_id,
                    "run_id": active_run_id,
                    "enqueued_at": entry.enqueued_at.isoformat() if entry else None,
                    "started_at": entry.started_at.isoformat() if entry and entry.started_at else None,
                }

            for idx, run_id in enumerate(self._pending, start=1):
                entry = self._entries.get(run_id)
                if entry and entry.session_id == session_id:
                    return {
                        "state": "queued",
                        "session_id": session_id,
                        "run_id": run_id,
                        "position": idx,
                        "queue_depth": len(self._pending),
                        "enqueued_at": entry.enqueued_at.isoformat(),
                    }
        return None

    async def snapshot(self) -> Dict[str, Any]:
        async with self._cond:
            pending_entries: List[Dict[str, Any]] = []
            for idx, run_id in enumerate(self._pending, start=1):
                entry = self._entries.get(run_id)
                if not entry:
                    continue
                pending_entries.append(
                    {
                        "position": idx,
                        "run_id": entry.run_id,
                        "session_id": entry.session_id,
                        "source": entry.source,
                        "enqueued_at": entry.enqueued_at.isoformat(),
                    }
                )

            active_entries: List[Dict[str, Any]] = []
            for session_id, run_id in self._active_by_session.items():
                entry = self._entries.get(run_id)
                active_entries.append(
                    {
                        "run_id": run_id,
                        "session_id": session_id,
                        "source": entry.source if entry else "api",
                        "enqueued_at": entry.enqueued_at.isoformat() if entry else None,
                        "started_at": entry.started_at.isoformat() if entry and entry.started_at else None,
                    }
                )

            return {
                "max_global_concurrency": self.max_global_concurrency,
                "active_count": len(self._active_by_session),
                "pending_count": len(self._pending),
                "active": active_entries,
                "pending": pending_entries,
            }

    @asynccontextmanager
    async def lease(
        self,
        session_id: str,
        source: str = "api",
        timeout_seconds: float = 0,
    ) -> AsyncIterator[QueueLease]:
        entry = await self.enqueue(session_id=session_id, source=source)
        lease = await self.acquire(entry, timeout_seconds=timeout_seconds)
        try:
            yield lease
        finally:
            await self.release(lease)
