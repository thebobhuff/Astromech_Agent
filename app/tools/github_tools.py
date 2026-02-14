from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests
from langchain.tools import tool


GITHUB_API_BASE = "https://api.github.com"


def _headers() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "astromech-github-client",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{GITHUB_API_BASE}{endpoint}"
    response = requests.request(method=method, url=url, headers=_headers(), json=payload, timeout=30)

    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    if response.status_code >= 400:
        message = data.get("message", response.text) if isinstance(data, dict) else str(data)
        return {
            "ok": False,
            "status": response.status_code,
            "error": message,
            "endpoint": endpoint,
        }

    return {
        "ok": True,
        "status": response.status_code,
        "data": data,
    }


@tool
def github_client(
    action: str,
    repo: str = "",
    title: str = "",
    body: str = "",
    state: str = "open",
    issue_number: int = 0,
    limit: int = 20,
    labels_csv: str = "",
) -> str:
    """
    GitHub API client for common issue/repository operations.

    Actions:
    - list_repos: list repositories for the authenticated user.
    - list_issues: list issues for a repo (requires repo "owner/name").
    - get_issue: get a single issue (requires repo and issue_number).
    - create_issue: create an issue (requires repo, title, body).
    """
    action = (action or "").strip().lower()

    if action == "list_repos":
        result = _request("GET", f"/user/repos?sort=updated&direction=desc&per_page={max(1, min(limit, 100))}")
        if not result["ok"]:
            return json.dumps(result, indent=2)
        repos = [
            {
                "full_name": r.get("full_name"),
                "private": r.get("private"),
                "html_url": r.get("html_url"),
                "updated_at": r.get("updated_at"),
            }
            for r in result["data"]
        ]
        return json.dumps({"ok": True, "action": action, "repos": repos}, indent=2)

    if action == "list_issues":
        if not repo:
            return "Error: 'repo' is required for list_issues (format: owner/name)."
        safe_state = state if state in {"open", "closed", "all"} else "open"
        per_page = max(1, min(limit, 100))
        result = _request("GET", f"/repos/{repo}/issues?state={safe_state}&per_page={per_page}")
        if not result["ok"]:
            return json.dumps(result, indent=2)
        issues = [
            {
                "number": i.get("number"),
                "title": i.get("title"),
                "state": i.get("state"),
                "html_url": i.get("html_url"),
                "created_at": i.get("created_at"),
                "updated_at": i.get("updated_at"),
                "user": (i.get("user") or {}).get("login"),
                "is_pull_request": "pull_request" in i,
            }
            for i in result["data"]
        ]
        return json.dumps({"ok": True, "action": action, "repo": repo, "issues": issues}, indent=2)

    if action == "get_issue":
        if not repo:
            return "Error: 'repo' is required for get_issue (format: owner/name)."
        if issue_number <= 0:
            return "Error: 'issue_number' must be > 0 for get_issue."
        result = _request("GET", f"/repos/{repo}/issues/{issue_number}")
        if not result["ok"]:
            return json.dumps(result, indent=2)
        issue = result["data"]
        payload = {
            "ok": True,
            "action": action,
            "repo": repo,
            "issue": {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "html_url": issue.get("html_url"),
                "body": issue.get("body"),
                "user": (issue.get("user") or {}).get("login"),
                "labels": [lbl.get("name") for lbl in issue.get("labels", [])],
            },
        }
        return json.dumps(payload, indent=2)

    if action == "create_issue":
        if not repo:
            return "Error: 'repo' is required for create_issue (format: owner/name)."
        if not title.strip():
            return "Error: 'title' is required for create_issue."
        if not body.strip():
            return "Error: 'body' is required for create_issue."

        labels = [label.strip() for label in labels_csv.split(",") if label.strip()]
        issue_payload: Dict[str, Any] = {"title": title, "body": body}
        if labels:
            issue_payload["labels"] = labels

        result = _request("POST", f"/repos/{repo}/issues", payload=issue_payload)
        if not result["ok"]:
            return json.dumps(result, indent=2)

        created = result["data"]
        output = {
            "ok": True,
            "action": action,
            "repo": repo,
            "issue": {
                "number": created.get("number"),
                "title": created.get("title"),
                "html_url": created.get("html_url"),
                "state": created.get("state"),
            },
        }
        return json.dumps(output, indent=2)

    return (
        "Error: Unknown action. Use one of: list_repos, list_issues, "
        "get_issue, create_issue."
    )


def get_github_tools():
    return [github_client]
