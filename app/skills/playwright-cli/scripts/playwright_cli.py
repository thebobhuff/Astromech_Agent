import argparse
import asyncio
import json
from pathlib import Path
from typing import Any


def _normalize_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def _parse_inline_step(raw_step: str) -> dict[str, Any]:
    if ":" not in raw_step:
        raise ValueError(f"Invalid step '{raw_step}'. Expected '<action>:<payload>'.")

    action, payload = raw_step.split(":", 1)
    action = action.strip().lower()
    payload = payload.strip()

    if action == "fill":
        if "=" not in payload:
            raise ValueError("fill step must be 'fill:<selector>=<value>'")
        selector, value = payload.split("=", 1)
        return {"action": "fill", "selector": selector.strip(), "value": value}

    if action == "click":
        return {"action": "click", "selector": payload}

    if action == "clickxy":
        if "," not in payload:
            raise ValueError("clickxy step must be 'clickxy:<x>,<y>'")
        x_str, y_str = payload.split(",", 1)
        return {"action": "clickxy", "x": int(x_str.strip()), "y": int(y_str.strip())}

    if action == "wait":
        return {"action": "wait", "ms": int(payload)}

    if action == "waitfor":
        return {"action": "waitfor", "selector": payload}

    if action == "press":
        if "=" not in payload:
            raise ValueError("press step must be 'press:<selector>=<key>'")
        selector, key = payload.split("=", 1)
        return {"action": "press", "selector": selector.strip(), "key": key.strip()}

    if action == "screenshot":
        return {"action": "screenshot", "path": payload or "screenshot.png"}

    raise ValueError(f"Unsupported action '{action}' in step '{raw_step}'.")


def _load_steps(steps_file: str | None, inline_steps: list[str] | None) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []

    if steps_file:
        raw = Path(steps_file).read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("--steps-file must contain a JSON array of step objects.")
        for item in parsed:
            if not isinstance(item, dict) or "action" not in item:
                raise ValueError("Each step from --steps-file must be an object with an 'action' field.")
            steps.append(item)

    for raw_step in inline_steps or []:
        steps.append(_parse_inline_step(raw_step))

    return steps


async def _run(url: str, steps: list[dict[str, Any]], headed: bool, timeout_ms: int) -> None:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        raise RuntimeError("Playwright is not installed. Install dependencies and run 'playwright install chromium'.") from exc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(timeout_ms)

        print(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded")

        for idx, step in enumerate(steps, 1):
            action = str(step.get("action", "")).strip().lower()
            print(f"[{idx}/{len(steps)}] {action}")

            if action == "fill":
                await page.fill(str(step["selector"]), str(step["value"]))
            elif action == "click":
                await page.click(str(step["selector"]))
            elif action == "clickxy":
                await page.mouse.click(int(step["x"]), int(step["y"]))
            elif action == "wait":
                await page.wait_for_timeout(int(step["ms"]))
            elif action == "waitfor":
                await page.wait_for_selector(str(step["selector"]))
            elif action == "press":
                await page.press(str(step["selector"]), str(step["key"]))
            elif action == "screenshot":
                path = str(step.get("path", "screenshot.png"))
                await page.screenshot(path=path, full_page=True)
                print(f"Saved screenshot: {path}")
            else:
                raise ValueError(f"Unsupported action in JSON step: {action}")

        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Playwright CLI helper for form filling, clicking, and scripted browser actions."
    )
    parser.add_argument("--url", required=True, help="Target URL to open before running steps.")
    parser.add_argument("--steps-file", help="Path to a JSON file containing step objects.")
    parser.add_argument(
        "--step",
        action="append",
        help="Inline step (repeatable). Example: fill:#email=user@example.com",
    )
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window.")
    parser.add_argument("--timeout-ms", type=int, default=30000, help="Default timeout per action.")
    args = parser.parse_args()

    url = _normalize_url(args.url)
    steps = _load_steps(args.steps_file, args.step)

    if not steps:
        raise ValueError("Provide at least one step via --step or --steps-file.")

    asyncio.run(_run(url=url, steps=steps, headed=args.headed, timeout_ms=args.timeout_ms))


if __name__ == "__main__":
    main()
