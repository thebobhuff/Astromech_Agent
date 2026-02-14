---
name: github-client
description: Interact with GitHub repositories, issues, and pull requests. Includes standard templates for commits and PRs.
---

# GitHub Client

Allows the agent to interact with GitHub to manage projects, track issues, and explore codebases.

## Prerequisites

- **Authentication**: `GITHUB_TOKEN` environment variable should be set for script-based access, OR the GitHub CLI (`gh`) must be authenticated.
- **CLI Installation**: GitHub CLI (`gh`) is required for PR operations.

## Executable Location

If `gh` is not in the system PATH, it is typically located at:
`C:\Program Files\GitHub CLI\gh.exe`

Always check this path if the `gh` command is not recognized.

## Usage

Use the `gh_tool.py` script for basic operations, or use the `gh` CLI directly for complex PR tasks.

### PR and Commit Template Standard

When creating commits or Pull Requests, always use the following structure for the description/body:

```markdown
# TLDR
[Summary of changes made in the session. Maximum 2 paragraphs.]

## Changes
- [Change 1]
- [Change 2]
- [Change 3]

## Database Changes/Migrations
- [Migration 1: Explanation] (If none, state "None")

# Technical Documentation
[All Technical documentation about the changes, architecture updates, or logic flow.]

# Destructive Code/Deletions
[Call out any code or features that were removed. If none, state "None".]
```

### Common Commands

#### List Repositories
```bash
python app/skills/github/scripts/gh_tool.py repos --limit 5
```

#### Create Pull Request
Use the CLI directly. If it fails, use the full path.

```bash
# Standard
gh pr create --title "Short Title" --body "Paste the template here"

# Using Absolute Path (Windows)
"C:\Program Files\GitHub CLI\gh.exe" pr create --title "Short Title" --body "Paste the template here"
```

## When to use

- When checking for existing bugs or feature requests.
- When creating tickets for planned work.
- When documenting work through Commits and Pull Requests.