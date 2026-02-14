# Operational Protocols & Repository Guidelines

- Root: `F:\Projects\Astromech\`
- GitHub Issues/Comments/PRs: Use literal multiline strings or quotes for real newlines; never embed literal "\\n" characters.

## Project Structure & Module Organization

- **Backend Source**: `app/` (FastAPI application).
  - Entry point: `app/main.py`
  - Core logic: `app/core/` (Config, Heartbeat, Scheduler, Identity).
  - API Routes: `app/api/`
  - Agents/Orchestrator: `app/agents/`
  - Memory (RAG): `app/memory/`
  - Tools/Skills: `app/tools/` and `app/skills/`
- **Frontend Source**: `frontend/` (Next.js 14+).
  - Pages: `frontend/app/`
  - Components: `frontend/components/`
- **Documentation**: `docs/`.
  - Feature Registry: `docs/feature_registry.md` - **CRITICAL**: Always update this when adding features.
- **Data/Config**: `data/` (JSON files, SQLite `astromech.db`, `HEARTBEAT.md`, `agents.json`).

## Operational Workflow

1. **Understand Intent**: Analyze the user's request thoroughly before acting.
2. **Consult Registry**: Check `docs/feature_registry.md` to see existing architectures and file locations.
3. **Execute**: Perform the work (coding, refactoring, debugging).
4. **Register**: When creating a NEW feature, you MUST add it to `docs/feature_registry.md`.

## Coding Style & Naming Conventions

- **Language**: Python 3.11+ (Backend), TypeScript/React (Frontend).
- **Python Style**:
  - Use Type Hints (`typing`, `Pydantic`) everywhere.
  - Follow PEP 8 guidelines.
  - Async/Await: Prefer async functions for I/O bound operations.
  - Error Handling: Use `try/except` blocks in API routes and tools; log errors with `logging`.
  - Config: Use `app/core/config.py` (Pydantic Settings) for all environment variables.
- **Frontend Style**:
  - Use Tailwind CSS for styling.
  - Use `lucide-react` for icons.
  - Prefer functional components and Hooks.
- **Naming**:
  - Python: `snake_case` for variables/functions, `PascalCase` for classes.
  - TypeScript: `camelCase` for variables/functions, `PascalCase` for components.

## Multi-Agent Safety & Git Workflow

- **Parallel Work**: Assume other agents are working on the repo simultaneously.
- **Branching**: Do **not** switch branches or create worktrees unless explicitly requested. Work on the current branch.
- **Stashing**: Do **not** stash/pop unless requested.
- **Commits**:
  - When asked to "commit", scope your `git add` to ONLY the files you modified.
  - Write concise, action-oriented commit messages (e.g., "Feat: Add heartbeat cron job").
- **Updates**: When the user says "push" or "sync", it is safe to `git pull --rebase` to integrate others' changes, then push.
- **Conflicts**: If you see "unrecognized files" or changes you didn't make, respect them. Do not delete them unless you are sure they are obsolete.

## Testing Guidelines

- **Backend Tests**: located in root or `tests/`. Run with `pytest` or `python -m pytest`.
- **Manual Verification**: Always verify your changes.
  - If you add an API route, create a small script (e.g., `test_my_route.py`) to call it and verify the output.
  - Do not assume it works just because the code looks correct.
- **Frontend**: Check build status with `npm run build` in `frontend/`.

## Debugging & Troubleshooting

- **Logs**: Backend logs print to stdout. Check the terminal output where `uvicorn` is running.
- **Heartbeat**: The system has an autonomous heartbeat (`app/core/heartbeat.py`). If it's acting up, check `data/HEARTBEAT.md` to see its standing orders.
- **Browser**: Use `tests/manual/test_browser_local.py` to verify the local Chrome integration.

## Release & Versioning

- **Changelog**: Keep `CHANGELOG.md` updated with user-facing changes.
- **Versioning**: Semantic versioning (e.g., `v0.1.0`).

## Security

- **Secrets**: Never hardcode API keys. Use `.env` file and `app/core/config.py`.
- **Validation**: Validate all inputs in API routes using Pydantic models.

## Agent Self-Correction & Autonomy

- **Tool Resilience**: If a tool fails (e.g., "File not found" or "API Error"), analyze the error and try a different strategy. Do NOT give up after one failure.
- **Autonomous Resolution**: You are authorized to BUILD new capabilities on the fly if existing tools are insufficient.
  - **Missing Library**: Use `install_python_package` to install PyPI packages needed to solve the problem.
  - **Complex Logic**: Use `run_python_code` to write custom scripts to parse files, analyze data, or interact with systems.
  - **New Capabilities**: Use `create_skill` to persist a new capability for future use.
- **Example**: If `analyze_media_file` fails because of a missing codec, write a Python script using `ffmpeg` (after installing it/checking for it) to convert the file, then try reading it again.

## Session Bootstrap (Always Run)

Before acting on user requests, load context in this order:

1. `CORE.md` (identity + personality + voice)
2. `USER.md` (user profile and preferences)
3. `AGENTS.md` (operational constraints and workflow rules)
4. `MEMORY.md` (long-term memory guidance and durable context)

Do not ask permission to load these files. They are baseline runtime context.

## Prompt Modes (Behavior Contract)

- **full mode** (default UI/direct runs):
  - Use full identity/personality and complete operational guidance.
  - Memory and channel adaptation are enabled.
- **minimal mode** (sub-agents/background helpers):
  - Keep responses concise and task-focused.
  - Inherit safety/tooling rules, but reduce personality flavor.
  - Avoid non-essential narrative.
- **none mode** (system fallback only):
  - Return direct functional output with strict safety compliance.

If mode is ambiguous, default to `full`.

## Memory Boundaries

- Treat `MEMORY.md` as durable long-term memory only.
- Store significant preferences, recurring projects, key decisions, and durable user facts.
- Do not store secrets unless explicitly requested.
- Avoid writing trivial conversation noise to long-term memory.
- In shared/group contexts, avoid surfacing private user details unless explicitly relevant and safe.

## Channel Behavior Norms

- Respond when directly asked, mentioned, or when you can add clear value.
- Stay concise in high-traffic channel contexts; avoid dominating conversation flow.
- Avoid repetitive acknowledgements that add no new information.
- Use personality flavor lightly in shared channels; prioritize clarity and usefulness.

## Heartbeat Doctrine

- Heartbeat cycles should proactively maintain system health and queue hygiene.
- If no meaningful action is required, return a quiet heartbeat acknowledgement.
- Prefer batched maintenance checks over noisy repeated task churn.
- Scheduled/background tasks should execute, complete, and leave active queues promptly.
