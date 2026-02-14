---
name: playwright-cli
description: Automate browser interactions with Playwright CLI workflows, including ordered form filling, selector clicks, and coordinate-based screen clicks. Use when tasks require logging in, submitting web forms, clicking buttons/links, or taking screenshots after UI actions.
---

# Playwright CLI

Run scripted browser actions with a deterministic step list.

## Prerequisites

- Ensure Python dependencies are installed (`playwright` is required).
- If browsers are not installed yet, run:

```bash
playwright install chromium
```

## Primary Script

Use `app/skills/playwright-cli/scripts/playwright_cli.py`.

## Quick Examples

### Fill a login form and submit

```bash
python app/skills/playwright-cli/scripts/playwright_cli.py ^
  --url "https://example.com/login" ^
  --step "fill:#email=user@example.com" ^
  --step "fill:#password=super-secret" ^
  --step "click:button[type='submit']" ^
  --step "wait:2000" ^
  --step "screenshot:login-result.png"
```

### Click by screen coordinates

```bash
python app/skills/playwright-cli/scripts/playwright_cli.py ^
  --url "https://example.com/canvas" ^
  --step "clickxy:420,315" ^
  --step "screenshot:clicked-point.png"
```

### Run steps from a JSON file

```bash
python app/skills/playwright-cli/scripts/playwright_cli.py --url "https://example.com" --steps-file steps.json
```

`steps.json` structure:

```json
[
  {"action": "fill", "selector": "#name", "value": "Ada Lovelace"},
  {"action": "click", "selector": "button[type='submit']"},
  {"action": "screenshot", "path": "result.png"}
]
```

## Step Syntax

- `fill:<selector>=<value>`
- `click:<selector>`
- `clickxy:<x>,<y>`
- `wait:<milliseconds>`
- `waitfor:<selector>`
- `press:<selector>=<key>`
- `screenshot:<path>`

## Notes

- Keep selectors specific (`#id`, `[name='field']`, or explicit button selectors) to reduce flaky runs.
- Prefer headless mode for automation; use `--headed` for troubleshooting interactive pages.
