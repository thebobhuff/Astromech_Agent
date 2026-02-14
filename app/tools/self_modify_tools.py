from __future__ import annotations

from pathlib import Path
from langchain.tools import tool


REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    resolved = candidate.resolve()

    if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
        raise ValueError(
            f"Path '{path}' is outside repository root '{REPO_ROOT}'."
        )
    return resolved


@tool
def self_modify_code(
    path: str,
    operation: str,
    content: str = "",
    search_text: str = "",
) -> str:
    """
    Modifies code/text files only inside the repository directory.

    Operations:
    - write: overwrite/create file with content
    - append: append content to end of file (creates file if needed)
    - replace: replace one exact occurrence of search_text with content
    """
    try:
        target = _resolve_repo_path(path)
    except Exception as exc:
        return f"Error: {exc}"

    if target.is_dir():
        return "Error: target path is a directory, not a file."

    operation = operation.strip().lower()
    if operation not in {"write", "append", "replace"}:
        return "Error: invalid operation. Use 'write', 'append', or 'replace'."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        if operation == "write":
            target.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} chars to {target}"

        if operation == "append":
            with target.open("a", encoding="utf-8") as f:
                f.write(content)
            return f"Appended {len(content)} chars to {target}"

        # replace
        if not target.exists():
            return "Error: file not found for replace operation."
        if not search_text:
            return "Error: search_text is required for replace operation."

        current = target.read_text(encoding="utf-8")
        occurrences = current.count(search_text)
        if occurrences == 0:
            return "Error: search_text not found in file."
        if occurrences > 1:
            return (
                "Error: search_text matched multiple places; provide a more "
                "specific search_text."
            )

        updated = current.replace(search_text, content, 1)
        target.write_text(updated, encoding="utf-8")
        return f"Replaced 1 occurrence in {target}"
    except Exception as exc:
        return f"Error modifying file: {exc}"


def get_self_modify_tools():
    return [self_modify_code]
