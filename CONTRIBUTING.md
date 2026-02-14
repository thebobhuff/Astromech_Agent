# Contributing

## Development Setup

1. Create Python virtual environment and install backend dependencies.
2. Install frontend dependencies in `frontend/`.
3. Copy `.env.example` to `.env` and configure required keys.

## Code Standards

- Backend: Python 3.11+, type hints, PEP 8.
- Frontend: TypeScript + React functional components.
- Keep edits scoped; avoid unrelated refactors in the same PR.

## Testing

- Run backend automated tests:

```bash
python -m pytest
```

- Run frontend build check:

```bash
cd frontend
npm run build
```

- Manual smoke scripts live in `tests/manual/` and are optional unless your change impacts those flows.

## Documentation Requirements

When adding a new feature, update:

1. `docs/feature_registry.md`
2. `CHANGELOG.md`
3. `README.md` when user-facing behavior/setup changes

## Pull Requests

1. Use clear, action-oriented titles.
2. Include a short test plan with commands run.
3. Link related issues.
4. Document config changes and new environment variables.