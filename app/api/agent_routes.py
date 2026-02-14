from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import sys
import platform
import os
import json
import asyncio
import logging
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
from app.agents.session_manager import SessionManager
from app.agents.orchestrator import AgentOrchestrator
from app.agents.registry import get_agent_registry
from app.core.models import AgentSession, AgentProfile
from app.core.identity import is_configured, load_identity, save_identity, AgentIdentity
from app.core.config import settings
from app.skills.loader import load_skills
from app.agents.run_registry import (
    abort_run, get_run_status, list_active_runs,
)
from app.agents.run_lane_queue import RunLaneQueue

from app.core.guardian import guardian
from app.core.scheduler import TaskQueue, encode_plan_description
from app.core.response_formatter import (
    format_response_for_channel,
    split_response_for_channel,
    normalize_channel,
)

router = APIRouter(tags=["Agent"])
logger = logging.getLogger(__name__)
run_lane_queue = RunLaneQueue(max_global_concurrency=settings.AGENT_MAX_CONCURRENT_RUNS)

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"
    images: Optional[List[str]] = None
    model: Optional[str] = None # Allow overriding model (e.g. "openai/gpt-4o")
    channel: str = "ui"  # ui | telegram | discord

class ChatResponse(BaseModel):
    response: str
    metadata: Dict[str, Any]
    session_id: str

class SystemStatus(BaseModel):
    platform: str
    python_version: str
    rag_enabled: bool
    skills_loaded: int
    workspace_path: str

class LLMConfig(BaseModel):
    provider: str
    model: str

class StatusResponse(BaseModel):
    configured: bool
    identity: Optional[AgentIdentity] = None
    system: Optional[SystemStatus] = None
    llm: Optional[LLMConfig] = None


class ApprovalActionResponse(BaseModel):
    action_id: str
    action_type: str
    status: str
    tool_name: str
    tool_args: Dict[str, Any]
    created_at: str

# Dependency Injection Providers
async def get_session_manager():
    return SessionManager()

async def get_orchestrator():
    return AgentOrchestrator()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest, 
    sessions: SessionManager = Depends(get_session_manager),
    agent: AgentOrchestrator = Depends(get_orchestrator)
):
    channel = normalize_channel(req.channel)
    queue_entry = await run_lane_queue.enqueue(session_id=req.session_id, source="chat")
    try:
        lease = await run_lane_queue.acquire(
            queue_entry,
            timeout_seconds=float(settings.AGENT_QUEUE_WAIT_TIMEOUT_SECONDS),
        )
    except asyncio.TimeoutError:
        await run_lane_queue.cancel(queue_entry.run_id)
        raise HTTPException(
            status_code=429,
            detail=(
                "Run queue wait timeout exceeded. "
                "Try again, cancel active runs, or increase AGENT_QUEUE_WAIT_TIMEOUT_SECONDS."
            ),
        )

    try:
        queue_wait_seconds = 0.0
        if queue_entry.started_at:
            queue_wait_seconds = max(
                0.0, (queue_entry.started_at - queue_entry.enqueued_at).total_seconds()
            )

        logger.info(
            "Chat request received",
            extra={"session_id": req.session_id, "event": "api_chat"},
        )
        # 1. Load Session State
        session = await sessions.load_session(req.session_id)
        
        # 2. Run Agent
        # The agent now returns an AgentResponse object which includes metadata and potentially updated session data
        result = await agent.run(
            req.prompt,
            images=req.images,
            session=session,
            model_override=req.model,
            source_channel=channel,
        )
        
        # 3. Save Updated Session State
        if result.session_data:
            await sessions.save_session(result.session_data)
        
        formatted_response = format_response_for_channel(result.response, channel)
        response_metadata = dict(result.metadata or {})
        response_metadata["channel"] = channel
        response_metadata["queue_wait_seconds"] = round(queue_wait_seconds, 3)
        return ChatResponse(
            response=formatted_response,
            metadata=response_metadata,
            session_id=session.session_id
        )
    except Exception as e:
        logger.exception(
            "Chat request failed: %s",
            e,
            extra={"session_id": req.session_id, "event": "api_chat"},
        )
        
        # Ensure we always return a response, even in case of detailed failure
        return ChatResponse(
            response=format_response_for_channel(
                f"I apologize, but I encountered a system error: {str(e)}",
                channel,
            ),
            metadata={"error": str(e), "status": "error", "channel": channel},
            session_id=req.session_id
        )
    finally:
        await run_lane_queue.release(lease)


@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    SSE streaming endpoint for chat. Yields server-sent events as the agent works:
      event: phase      — pipeline stage changes (evaluating, memory, routing, executing)
      event: intent     — evaluated intent
      event: tool_start — tool execution beginning (with tool names)
      event: tool_done  — tool execution finished (with result previews)
      event: response_chunk — incremental assistant text chunks
      event: complete   — final response + metadata
      event: error      — if something goes wrong
    """
    channel = normalize_channel(req.channel)
    sessions = SessionManager()
    agent = AgentOrchestrator()
    logger.info(
        "Streaming chat request received",
        extra={"session_id": req.session_id, "event": "api_chat_stream"},
    )

    async def event_generator():
        event_queue: asyncio.Queue = asyncio.Queue()

        async def stream_callback(event: str, data: Dict[str, Any]):
            await event_queue.put((event, data))

        async def run_agent():
            queue_entry = await run_lane_queue.enqueue(session_id=req.session_id, source="chat_stream")
            lease = None
            try:
                queue_status = await run_lane_queue.get_session_queue_status(req.session_id)
                if queue_status and queue_status.get("state") == "queued":
                    await event_queue.put(
                        (
                            "phase",
                            {
                                "phase": "queued",
                                "message": "Waiting for run lane...",
                                "position": queue_status.get("position", 1),
                                "queue_depth": queue_status.get("queue_depth", 1),
                            },
                        )
                    )

                lease = await run_lane_queue.acquire(
                    queue_entry,
                    timeout_seconds=float(settings.AGENT_QUEUE_WAIT_TIMEOUT_SECONDS),
                )

                wait_seconds = 0.0
                if queue_entry.started_at:
                    wait_seconds = max(
                        0.0,
                        (queue_entry.started_at - queue_entry.enqueued_at).total_seconds(),
                    )
                await event_queue.put(
                    (
                        "phase",
                        {
                            "phase": "queued_done",
                            "message": "Run lane acquired.",
                            "wait_seconds": round(wait_seconds, 3),
                        },
                    )
                )

                session = await sessions.load_session(req.session_id)
                result = await agent.run(
                    req.prompt,
                    images=req.images,
                    session=session,
                    model_override=req.model,
                    stream_callback=stream_callback,
                    source_channel=channel,
                )
                if result.session_data:
                    await sessions.save_session(result.session_data)
                # Signal completion to the queue reader
                await event_queue.put(("__done__", {}))
            except asyncio.TimeoutError:
                await run_lane_queue.cancel(queue_entry.run_id)
                await event_queue.put(
                    (
                        "error",
                        {
                            "message": (
                                "Run queue wait timeout exceeded. "
                                "Try again, cancel active runs, or increase AGENT_QUEUE_WAIT_TIMEOUT_SECONDS."
                            )
                        },
                    )
                )
                await event_queue.put(("__done__", {}))
            except Exception as e:
                logger.exception(
                    "Streaming chat request failed: %s",
                    e,
                    extra={"session_id": req.session_id, "event": "api_chat_stream"},
                )
                await event_queue.put(("error", {"message": str(e)}))
                await event_queue.put(("__done__", {}))
            finally:
                if lease is not None:
                    await run_lane_queue.release(lease)
                else:
                    await run_lane_queue.cancel(queue_entry.run_id)

        # Launch agent in background task
        task = asyncio.create_task(run_agent())

        try:
            while True:
                try:
                    event, data = await asyncio.wait_for(event_queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"event: keepalive\ndata: {{}}\n\n"
                    continue

                if event == "__done__":
                    break

                if event == "complete":
                    full_response = format_response_for_channel(str(data.get("response") or ""), channel)
                    data["response"] = full_response
                    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
                    metadata["channel"] = channel
                    data["metadata"] = metadata

                    if full_response:
                        for chunk in split_response_for_channel(full_response, channel):
                            yield (
                                "event: response_chunk\n"
                                f"data: {json.dumps({'text': chunk}, default=str)}\n\n"
                            )
                            await asyncio.sleep(0.01)

                yield f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status", response_model=StatusResponse)
async def get_agent_status():
    identity = load_identity()
    skills = load_skills()
    
    system = SystemStatus(
        platform=platform.platform(),
        python_version=sys.version.split()[0],
        rag_enabled=True,  # Defaulting, check config if variable exists
        skills_loaded=len(skills),
        workspace_path=os.getcwd()
    )
    
    llm_conf = LLMConfig(
        provider=settings.DEFAULT_LLM_PROVIDER,
        model=settings.OLLAMA_MODEL if settings.DEFAULT_LLM_PROVIDER == "ollama" else "auto"
    )

    return StatusResponse(
        configured=is_configured(),
        identity=identity,
        system=system,
        llm=llm_conf
    )

@router.post("/configure")
async def configure_agent(identity: AgentIdentity):
    try:
        save_identity(identity)
        return {"status": "success", "message": "Identity updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles", response_model=List[AgentProfile])
async def list_agent_profiles():
    return get_agent_registry().list_agents()

@router.post("/profiles", response_model=AgentProfile)
async def create_agent_profile(profile: AgentProfile):
    try:
        get_agent_registry().register_agent(profile)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{session_id}")
async def clear_history(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager)
):
    # Overwrite with empty session
    new_session = AgentSession(session_id=session_id)
    await sessions.save_session(new_session)
    return {"status": "cleared", "session_id": session_id}

@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager)
):
    session = await sessions.load_session(session_id)
    return session

@router.post("/approve/{action_id}")
async def approve_action(action_id: str):
    success = guardian.approve_action(action_id)
    if success:
        action = guardian.get_action(action_id)
        if action and action.action_type == "plan_approval" and action.status == "approved":
            payload = action.tool_args or {}
            plan = payload.get("plan", {}) if isinstance(payload, dict) else {}
            steps = plan.get("steps", []) if isinstance(plan, dict) else []
            queue = TaskQueue()
            created_tasks = []
            plan_name = str(plan.get("name", "Execution Plan"))
            goal = str(payload.get("goal", ""))

            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_id = str(step.get("id") or "")
                title = str(step.get("title") or f"Plan step {step_id or 'unknown'}")
                description = str(step.get("description") or "")
                depends_on = step.get("depends_on", [])
                if not isinstance(depends_on, list):
                    depends_on = []
                parallelizable = bool(step.get("parallelizable", False))
                priority = int(step.get("priority", 3) or 3)
                priority = min(max(priority, 1), 5)

                meta = {
                    "plan_action_id": action_id,
                    "step_id": step_id,
                    "depends_on": [str(d) for d in depends_on],
                    "parallelizable": parallelizable,
                    "goal": goal,
                }
                full_description = encode_plan_description(description, meta)
                task = queue.add_task(
                    title=f"[Plan] {plan_name}: {title}",
                    description=full_description,
                    priority=priority,
                )
                created_tasks.append(
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "step_id": step_id,
                        "depends_on": meta["depends_on"],
                        "parallelizable": parallelizable,
                        "priority": priority,
                    }
                )

            guardian.consume_action(action_id)
            return {
                "status": "approved_and_enqueued",
                "action_id": action_id,
                "tasks_created": created_tasks,
            }

        return {"status": "approved", "action_id": action_id}
    else:
        raise HTTPException(status_code=404, detail="Action ID not found or invalid.")

@router.post("/reject/{action_id}")
async def reject_action(action_id: str):
    success = guardian.reject_action(action_id)
    if success:
         return {"status": "rejected", "action_id": action_id}
    else:
        raise HTTPException(status_code=404, detail="Action ID not found.")


@router.get("/approvals", response_model=List[ApprovalActionResponse])
async def list_pending_approvals(action_type: Optional[str] = None):
    actions = guardian.list_pending_actions(action_type=action_type)
    return [
        ApprovalActionResponse(
            action_id=a.id,
            action_type=a.action_type,
            status=a.status,
            tool_name=a.tool_name,
            tool_args=a.tool_args,
            created_at=a.created_at.isoformat(),
        )
        for a in actions
    ]


@router.get("/approvals/{action_id}", response_model=ApprovalActionResponse)
async def get_approval(action_id: str):
    action = guardian.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action ID not found.")
    return ApprovalActionResponse(
        action_id=action.id,
        action_type=action.action_type,
        status=action.status,
        tool_name=action.tool_name,
        tool_args=action.tool_args,
        created_at=action.created_at.isoformat(),
    )


# --- Run Management (Abort / Cancel / Steer) ---

class SteerRequest(BaseModel):
    message: str


class UploadResponse(BaseModel):
    filename: str
    original_filename: str
    path: str
    size: int
    mime_type: str
    pinned_to_context: bool
    uploaded_at: str


_SAFE_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


def _validate_session_id(session_id: str) -> str:
    if not _SAFE_SESSION_RE.match(session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id. Allowed chars: letters, digits, underscore, hyphen.",
        )
    return session_id


def _safe_filename(name: Optional[str]) -> str:
    if not name:
        return "uploaded_file"
    base = os.path.basename(name).replace("\x00", "")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe[:180] or "uploaded_file"


@router.post("/uploads", response_model=UploadResponse)
async def upload_chat_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    pin_to_context: bool = Form(True),
    sessions: SessionManager = Depends(get_session_manager),
):
    session_id = _validate_session_id(session_id)

    uploads_root = Path("data") / "uploads" / session_id
    uploads_root.mkdir(parents=True, exist_ok=True)

    original_name = _safe_filename(file.filename)
    unique_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}_{original_name}"
    destination = uploads_root / unique_name

    max_bytes = 25 * 1024 * 1024
    total_bytes = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="File too large. Max supported upload size is 25MB.",
                    )
                out.write(chunk)
    except HTTPException:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    abs_path = str(destination.resolve())
    session = await sessions.load_session(session_id)

    if pin_to_context and abs_path not in session.context_files:
        session.context_files.append(abs_path)

    upload_record = {
        "filename": unique_name,
        "original_filename": original_name,
        "path": abs_path,
        "size": total_bytes,
        "mime_type": file.content_type or "application/octet-stream",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    uploaded = session.metadata.get("uploaded_files", [])
    if not isinstance(uploaded, list):
        uploaded = []
    uploaded.append(upload_record)
    session.metadata["uploaded_files"] = uploaded[-100:]

    await sessions.save_session(session)

    return UploadResponse(
        filename=upload_record["filename"],
        original_filename=upload_record["original_filename"],
        path=upload_record["path"],
        size=upload_record["size"],
        mime_type=upload_record["mime_type"],
        pinned_to_context=pin_to_context,
        uploaded_at=upload_record["uploaded_at"],
    )


@router.get("/uploads/{session_id}")
async def list_chat_uploads(
    session_id: str,
    sessions: SessionManager = Depends(get_session_manager),
):
    session = await sessions.load_session(_validate_session_id(session_id))
    uploaded = session.metadata.get("uploaded_files", [])
    if not isinstance(uploaded, list):
        uploaded = []
    return {
        "session_id": session_id,
        "uploaded_files": uploaded,
        "context_files": session.context_files,
    }

@router.post("/runs/{session_id}/abort")
async def abort_agent_run(session_id: str, reason: str = "user_cancelled"):
    """Abort an active agent run. The orchestrator will stop at the next checkpoint."""
    success = abort_run(session_id, reason=reason)
    if success:
        return {"status": "aborted", "session_id": session_id, "reason": reason}
    else:
        raise HTTPException(status_code=404, detail=f"No active run found for session '{session_id}'.")

@router.get("/runs/{session_id}/status")
async def get_agent_run_status(session_id: str):
    """Check the status of an active agent run."""
    handle = get_run_status(session_id)
    queue_state = await run_lane_queue.get_session_queue_status(session_id)
    if handle is None:
        if queue_state and queue_state.get("state") == "queued":
            return {
                "status": "queued",
                "session_id": session_id,
                "queue_position": queue_state.get("position"),
                "queue_depth": queue_state.get("queue_depth"),
                "queued_at": queue_state.get("enqueued_at"),
            }
        return {"status": "idle", "session_id": session_id}
    return {
        "status": handle.status,
        "session_id": handle.session_id,
        "current_turn": handle.current_turn,
        "max_turns": handle.max_turns,
        "started_at": handle.started_at.isoformat(),
        "cancel_reason": handle.cancel_reason,
    }

@router.get("/runs")
async def list_agent_runs():
    """List all currently active agent runs."""
    runs = list_active_runs()
    return [
        {
            "session_id": r.session_id,
            "status": r.status,
            "current_turn": r.current_turn,
            "max_turns": r.max_turns,
            "started_at": r.started_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/runs/queue")
async def get_run_queue_snapshot():
    """Inspect lane queue state (pending + active leasing)."""
    return await run_lane_queue.snapshot()

@router.post("/runs/{session_id}/steer")
async def steer_agent_run(session_id: str, req: SteerRequest):
    """Inject a message into an active agent run (mid-run course correction)."""
    handle = get_run_status(session_id)
    if handle is None or handle.status != "running":
        raise HTTPException(status_code=404, detail=f"No active run found for session '{session_id}'.")
    handle.steer_queue.put_nowait(req.message)
    return {"status": "steered", "session_id": session_id, "message": req.message}
