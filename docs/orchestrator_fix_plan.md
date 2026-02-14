# Orchestrator Fix Plan — 14 Bugs

**Created**: 2026-02-07  
**Status**: In Progress  

## Summary

Full audit of `app/agents/orchestrator.py` and supporting modules identified 14 bugs
ranging from critical (blocking the async event loop) to low (code quality). All fixes
are being implemented in a single pass.

---

## Phase 1 — Stop the Bleeding

| # | Bug | Severity | File(s) | Fix |
|---|-----|----------|---------|-----|
| 1 | `_evaluate_prompt` and `_route_request` call `chain.invoke()` (synchronous) inside `async` methods — blocks the FastAPI event loop | CRITICAL | `orchestrator.py` | Change to `await chain.ainvoke()` |
| 2 | Stale `RunHandle` reuse after `register_run` ValueError — previous abort_event may already be set, silently cancelling the new run | CRITICAL | `orchestrator.py` | `complete_run()` the stale entry then re-register fresh |
| 4 | No `temperature` parameter on Gemini LLM — function calling is non-deterministic | HIGH | `llm.py` | Add `temperature=0.2` for Gemini |
| 6 | Default model `gemini-2.5-flash-lite` has weak/absent function-calling support | HIGH | `models.json` | Switch default to `gemini-2.5-flash` |

## Phase 2 — Improve Tool Reliability

| # | Bug | Severity | File(s) | Fix |
|---|-----|----------|---------|-----|
| 5 | 28 tools bound at once exceeds Gemini's 10-20 recommended limit | HIGH | `orchestrator.py` | Dynamic tool filtering — bind router-selected + core set (max ~18) |
| 9 | Nudge counter inflated by non-nudge `[SYSTEM:` messages (wrap-up, steer, loop-break) | MEDIUM | `orchestrator.py` | Track nudges with dedicated counter, not message scan |
| 10 | ToolMessage restored with `name="tool"` — actual tool name is lost | MEDIUM | `session_manager.py`, `models.py` | Add `tool_name` field, store/restore correctly |

## Phase 3 — Robustness

| # | Bug | Severity | File(s) | Fix |
|---|-----|----------|---------|-----|
| 3 | `str(msg.content)` corrupts multimodal list content on session save | CRITICAL | `session_manager.py` | Use `json.dumps` for list content, `json.loads` on restore |
| 7 | `asyncio.Event`/`Queue` in `RunHandle` may bind to wrong event loop | HIGH | `run_registry.py` | Lazy-create primitives inside `register_run()` |
| 8 | `update_run_turn()` auto-aborts at `>=` before loop checks abort flag | MEDIUM | `orchestrator.py` | Move call after abort check, use `>` |
| 11 | Context window counts groups (10) not tokens — can exceed limits | MEDIUM | `context_manager.py` | Add approximate token-budget check |
| 12 | Failover model switch doesn't adapt system prompt formatting | MEDIUM | `orchestrator.py` | Rebuild system prompt on provider change |

## Phase 4 — Infrastructure & Cleanup

| # | Bug | Severity | File(s) | Fix |
|---|-----|----------|---------|-----|
| 13 | Embedding backends both broken — memory/RAG always returns 0 results | MEDIUM | `rag.py`, config | Switch to working embedding model, add health check |
| 14 | `for/else` exhaustion clause is fragile and can duplicate wrap-up | LOW | `orchestrator.py` | Refactor loop to explicit state machine |

---

## Files Modified

- `app/agents/orchestrator.py`
- `app/agents/session_manager.py`
- `app/agents/context_manager.py`
- `app/agents/run_registry.py`
- `app/core/llm.py`
- `app/core/models.py`
- `app/memory/rag.py`
- `data/models.json`
