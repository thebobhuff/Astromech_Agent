# Long Term Memory

(This file is updated by the agent to store long-term information)

- Project started: 2024

## What Belongs Here

- Durable user preferences and communication style
- Recurring projects and long-running goals
- Important decisions, constraints, and standing operating context
- Stable facts that improve future assistance quality

## What Does Not Belong Here

- Ephemeral chat filler
- One-off status messages with no future value
- Raw secrets unless explicitly requested to retain
- Verbose logs better suited for transient/session history

## Write Policy

- Prefer concise, high-signal entries.
- Deduplicate before writing new facts.
- Update existing entries when facts change, rather than appending conflicting copies.
- Use long-term memory only when information is genuinely worth recalling across sessions.

## Privacy and Context Boundaries

- In direct/private sessions: memory can be used normally.
- In shared/group contexts: avoid exposing private user facts unless explicitly needed for the task.
