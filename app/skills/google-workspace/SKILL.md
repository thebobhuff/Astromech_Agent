---
description: Manage files on Google Drive (local mount) and interact with Gmail (API).
name: google-workspace
---

# Google Workspace Skill

This skill provides tools for interacting with Google Drive and Gmail.


## Google Drive (Local)

Google Drive is mounted locally at `G:\My Drive`. You can use standard terminal commands (`dir`, `copy`, `del`) or the provided helper script.

### Usage
```bash
python app/skills/google-workspace/scripts/drive_tool.py list [path]
```

## Gmail (API)

Interacting with Gmail requires OAuth credentials.


### Setup
1. Place `credentials.json` from Google Cloud Console in the root directory.
2. The first run will open a browser for authentication and save `token.json`.


### Usage
```bash
python app/skills/google-workspace/scripts/gmail_tool.py list
```

## When to use
- When the user asks to find, read, or manage files in their Google Drive.
- When the user asks to check, read, or send emails via Gmail.

## Response
- Always Respond with the amount of unread emails.
- If there are no unread emails, just say there were 0, or none.
- If you were having an issue, try to report the full error.