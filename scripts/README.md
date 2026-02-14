# Scripts Directory

This directory contains operational and internal utility scripts.

## Layout

- `scripts/debug/`: ad-hoc diagnostics and route/session inspection helpers.
- `scripts/maintenance/`: cleanup and maintenance tasks for memory/session data.
- `scripts/integrations/google_workspace/`: Gmail/Google Workspace helper scripts.
- `scripts/llm/`: local model/provider helper CLIs.

## Usage Notes

- Run scripts from repository root where possible.
- Most scripts now resolve repository paths automatically and are safe to invoke from other working directories.
- Treat integration scripts as operator tooling, not public runtime API surface.
