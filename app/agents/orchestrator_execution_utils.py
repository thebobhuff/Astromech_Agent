from typing import Any, Optional


def extract_text_content(content: Any) -> Optional[str]:
    if isinstance(content, list):
        text_content = ""
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_content += block.get("text", "")
            elif isinstance(block, str):
                text_content += block
        return text_content.strip() if text_content.strip() else None
    if content and str(content).strip():
        return str(content).strip()
    return None


def is_hallucinated_tool_text(answer: str) -> bool:
    lower_ans = answer.lower()
    if "**tool call**" in lower_ans:
        return True
    if "executing tool" in lower_ans and len(answer) < 200:
        return True
    return False


def is_placeholder_text(answer: str) -> bool:
    return answer.strip('() ').lower() in (
        'empty response',
        'calling tools',
        'thinking',
        'continued',
        'system',
    )
