# Open Source Release Audit

Date: 2026-02-14

## Summary

This repository is feature-rich and operationally capable, but release hygiene needed alignment for external contributors.
This pass addressed immediate structure/documentation gaps and identified follow-up priorities.

## Changes Applied In This Pass

1. Consolidated root-level test scripts into a single `tests/` tree.
   - Automated tests: `tests/unit/`
   - Manual smoke scripts: `tests/manual/`
2. Added `pytest.ini` to make CI/local test runs deterministic (`tests/unit` only).
3. Updated `.gitignore` with pytest/coverage artifacts.
4. Rewrote root `README.md` for contributor onboarding and repeatable setup/testing.
5. Added this audit document to track release readiness work.

## High-Priority Release Gaps (Next)

1. CI pipeline
   - Add GitHub Actions for backend tests and frontend build checks.
2. Dependency hardening
   - Current `requirements.txt` is large and broad; split into runtime/dev constraints and pin with update policy.
3. Repository scope hygiene
   - Validate whether bundled side projects and binary assets should remain in this repo for public release.
4. Security policy
   - Add `SECURITY.md` with disclosure contact/process.
5. Issue/PR templates
   - Add `.github/ISSUE_TEMPLATE` and pull request template for consistent triage.

## Medium-Priority Improvements

1. Add backend lint/type checks (`ruff`, `mypy`) and frontend lint in CI.
2. Add architecture docs for the orchestrator module split and tool approval model.
3. Add smoke-test runner wrappers for `tests/manual/` with prerequisites listed per script.
4. Add `CONTRIBUTING.md` (if not present) with coding/testing/commit conventions.

## Risk Notes

1. Existing worktree contains many unrelated modified/untracked files from ongoing work; release branch should be cut from a stabilized baseline.
2. Several manual scripts depend on local services and keys; they are intentionally excluded from default pytest execution.