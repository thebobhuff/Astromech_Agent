from __future__ import annotations

import logging
import os
import re
from typing import List
from pydantic import BaseModel, Field
from app.memory.relationship_memory import (
    RelationshipFactInput,
    RelationshipMemoryStore,
)

logger = logging.getLogger(__name__)

USER_FILE = "USER.md"

_FIRST_PERSON_RE = re.compile(r"\b(i|i'm|im|i’ve|i'd|i’ll|my|me)\b", re.IGNORECASE)
_TASK_REQUEST_RE = re.compile(
    r"\b(i need you to|i want you to|can you|could you|will you|please)\b",
    re.IGNORECASE,
)
_PREFERENCE_CUE_RE = re.compile(
    r"\b("
    r"i (?:really\s+)?(?:like|love|prefer|enjoy|hate|dislike|favor|favour)|"
    r"i(?:'m| am) (?:into|a fan of)|"
    r"my (?:preference|preferred)|"
    r"i (?:usually|typically|always|often|rarely|never)|"
    r"i (?:use|work with|work on|code in)"
    r")\b",
    re.IGNORECASE,
)
_TRANSIENT_STATE_RE = re.compile(
    r"\b(i(?:'m| am) (?:tired|sleepy|hungry|thirsty|sick|ready|busy|stuck|confused|lost))\b",
    re.IGNORECASE,
)
_COMMUNICATION_STYLE_RE = re.compile(
    r"\b(concise|brief|short|detailed|step[- ]by[- ]step|direct|formal|casual|bullet points?|tone|style)\b",
    re.IGNORECASE,
)
_PROJECT_RE = re.compile(
    r"\b(project|working on|building|shipping|maintaining|roadmap|product)\b",
    re.IGNORECASE,
)
_HABIT_RE = re.compile(
    r"\b(usually|typically|always|often|rarely|never|every day|daily|weekly)\b",
    re.IGNORECASE,
)


class UserFactCandidate(BaseModel):
    fact: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.7


def _normalize(text: str) -> str:
    cleaned = text.strip().rstrip(".!?")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_preference_candidates(prompt: str) -> List[str]:
    """Extract preference-like first-person statements from free-form user text."""
    if not prompt or not prompt.strip():
        return []

    # Split on sentence boundaries/newlines to keep candidates concise.
    chunks = [
        _normalize(c)
        for c in re.split(r"[.!?\n]+", prompt)
        if c and c.strip()
    ]

    candidates: List[str] = []
    seen = set()
    for chunk in chunks:
        lower_chunk = chunk.lower()
        if not _FIRST_PERSON_RE.search(lower_chunk):
            continue
        if _TASK_REQUEST_RE.search(lower_chunk):
            continue
        if _TRANSIENT_STATE_RE.search(lower_chunk):
            continue

        # Keep only likely preference/profile statements.
        if _PREFERENCE_CUE_RE.search(lower_chunk):
            if lower_chunk not in seen:
                seen.add(lower_chunk)
                candidates.append(chunk)
            continue

        # Fallback for "I'm/Im/I am ..." profile statements.
        if re.search(r"\b(i(?:'m| am)|im)\s+\w+", lower_chunk):
            if lower_chunk not in seen:
                seen.add(lower_chunk)
                candidates.append(chunk)

    return candidates


def extract_durable_user_facts(prompt: str) -> List[UserFactCandidate]:
    """
    Extract durable relationship facts with tags/confidence.
    These are suitable for the dedicated relationship memory tier.
    """
    statements = extract_preference_candidates(prompt)
    facts: List[UserFactCandidate] = []
    seen = set()

    for statement in statements:
        normalized = _normalize(statement)
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)

        tags = {"preference"}
        confidence = 0.62
        lower = key

        if _HABIT_RE.search(lower):
            tags.add("habit")
            confidence += 0.15
        if _PROJECT_RE.search(lower):
            tags.add("recurring_project")
            confidence += 0.15
        if _COMMUNICATION_STYLE_RE.search(lower):
            tags.add("communication_style")
            confidence += 0.20
        if re.search(r"\b(prefer|like|love|enjoy|hate|dislike|fan of|into)\b", lower):
            confidence += 0.10

        # Penalize ambiguous/transient wording.
        if re.search(r"\b(maybe|sometimes|trying|for now|today)\b", lower):
            confidence -= 0.10

        facts.append(
            UserFactCandidate(
                fact=normalized,
                tags=sorted(tags),
                confidence=max(0.5, min(0.95, confidence)),
            )
        )

    return facts


def _upsert_preferences_section(content: str, items: List[str]) -> str:
    lines = content.splitlines()
    pref_idx = -1

    for i, line in enumerate(lines):
        if re.match(r"^\s*-\s*\*\*Preferences\*\*:\s*$", line, flags=re.IGNORECASE):
            pref_idx = i
            break
        if re.match(r"^\s*#+\s*Preferences\s*$", line, flags=re.IGNORECASE):
            pref_idx = i
            break

    if pref_idx == -1:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("- **Preferences**:")
        pref_idx = len(lines) - 1

    # Identify existing preference bullets directly under Preferences.
    existing_norm = set()
    insert_at = pref_idx + 1
    i = pref_idx + 1
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        # Stop when a new section-like block starts.
        if re.match(r"^\s*-\s*\*\*[A-Za-z][^*]*\*\*:\s*$", raw) or re.match(
            r"^\s*#+\s+", raw
        ):
            break
        bullet_match = re.match(r"^\s*[-*]\s+(.*)$", raw)
        if bullet_match:
            value = _normalize(bullet_match.group(1))
            if value and value.lower() != "(to be learned)":
                existing_norm.add(value.lower())
        i += 1

    insert_at = i

    to_add = []
    for item in items:
        normalized = _normalize(item)
        if not normalized:
            continue
        if normalized.lower() in existing_norm:
            continue
        existing_norm.add(normalized.lower())
        to_add.append(f"    - {normalized}")

    # Remove placeholder line if we are about to add real preferences.
    if to_add:
        j = pref_idx + 1
        while j < len(lines):
            if re.match(r"^\s*-\s*\*\*[A-Za-z][^*]*\*\*:\s*$", lines[j]) or re.match(
                r"^\s*#+\s+", lines[j]
            ):
                break
            if re.match(r"^\s*[-*]\s+\(To be learned\)\s*$", lines[j], flags=re.IGNORECASE):
                lines.pop(j)
                insert_at = max(pref_idx + 1, insert_at - 1)
                continue
            j += 1

        lines[insert_at:insert_at] = to_add

    return "\n".join(lines).rstrip() + "\n"


def evaluate_and_update_user_preferences(
    prompt: str,
    user_file: str = USER_FILE,
    relationship_store: RelationshipMemoryStore | None = None,
) -> List[str]:
    """
    Evaluate user prompt for first-person preference/profile statements and persist
    new items under USER.md Preferences.
    Returns the list of newly added preference lines.
    """
    items = extract_preference_candidates(prompt)
    durable_facts = extract_durable_user_facts(prompt)
    if not items:
        # Even when no plain preference line is extracted, preserve chance to store
        # structured durable facts if present.
        if durable_facts:
            try:
                rel_store = relationship_store or RelationshipMemoryStore()
                rel_store.upsert_facts(
                    [
                        RelationshipFactInput(
                            fact=f.fact,
                            tags=f.tags,
                            confidence=f.confidence,
                        )
                        for f in durable_facts
                    ],
                    source="user_profile_auto",
                )
            except Exception as rel_err:
                logger.debug("Relationship memory update skipped: %s", rel_err)
        return []

    current = ""
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            current = f.read()
    else:
        current = "# User Profile\n\n- **Name**: User\n- **Role**: Unknown\n- **Preferences**:\n    - (To be learned)\n"

    existing_before = {
        _normalize(x).lower()
        for x in re.findall(r"^\s*[-*]\s+(.*)$", current, flags=re.MULTILINE)
    }
    updated = _upsert_preferences_section(current, items)
    if updated != current:
        with open(user_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        logger.info("Updated user preferences in %s", user_file)

    # Compute which items were newly inserted.
    added: List[str] = []
    final_norm = {
        _normalize(x).lower()
        for x in re.findall(r"^\s*[-*]\s+(.*)$", updated, flags=re.MULTILINE)
    }
    for item in items:
        normalized = _normalize(item)
        if (
            normalized
            and normalized.lower() in final_norm
            and normalized.lower() not in existing_before
        ):
            added.append(normalized)

    # Persist structured relationship memory facts (with tags/confidence/date metadata)
    if durable_facts:
        try:
            rel_store = relationship_store or RelationshipMemoryStore()
            rel_store.upsert_facts(
                [
                    RelationshipFactInput(
                        fact=f.fact,
                        tags=f.tags,
                        confidence=f.confidence,
                    )
                    for f in durable_facts
                ],
                source="user_profile_auto",
            )
        except Exception as rel_err:
            logger.debug("Relationship memory update skipped: %s", rel_err)
    return added
