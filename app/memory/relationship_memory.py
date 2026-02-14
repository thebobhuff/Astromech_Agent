from __future__ import annotations

import json
import logging
import os
import re
from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger(__name__)

def _normalize_fact(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().rstrip(".!?"))
    return cleaned


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class RelationshipFactInput(BaseModel):
    fact: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.7


class RelationshipFact(BaseModel):
    fact: str
    normalized_fact: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = 0.7
    first_confirmed: str = Field(default_factory=lambda: date.today().isoformat())
    last_confirmed: str = Field(default_factory=lambda: date.today().isoformat())
    confirmations: int = 1
    source: str = "user_profile_auto"


class RelationshipMemoryStoreModel(BaseModel):
    profile_id: str = "default_user"
    facts: List[RelationshipFact] = Field(default_factory=list)


class RelationshipMemoryStore:
    """
    Structured durable-memory tier for user relationship context.
    Stores preferences, habits, recurring projects, and communication style.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            storage_path = settings.RELATIONSHIP_MEMORY_FILE
        self.storage_path = os.path.abspath(storage_path)
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load(self) -> RelationshipMemoryStoreModel:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return RelationshipMemoryStoreModel(**json.load(f))
            except Exception as e:
                logger.warning("Failed loading relationship memory store: %s", e)
        return RelationshipMemoryStoreModel()

    def _save(self, store: RelationshipMemoryStoreModel) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(store.model_dump(mode="json"), f, indent=2)

    def upsert_facts(
        self,
        facts: List[RelationshipFactInput],
        source: str = "user_profile_auto",
    ) -> List[RelationshipFact]:
        if not facts:
            return []

        today = date.today().isoformat()
        store = self._load()
        by_norm: Dict[str, RelationshipFact] = {
            f.normalized_fact: f for f in store.facts
        }
        changed: List[RelationshipFact] = []

        for item in facts:
            normalized = _normalize_fact(item.fact)
            if not normalized:
                continue
            tags = sorted({t.strip().lower() for t in item.tags if t and t.strip()})
            confidence = _clamp_confidence(item.confidence)

            existing = by_norm.get(normalized.lower())
            if existing:
                existing.tags = sorted(set(existing.tags) | set(tags))
                existing.last_confirmed = today
                existing.confirmations += 1
                # Repeated confirmations increase confidence slightly.
                existing.confidence = _clamp_confidence(
                    max(existing.confidence, confidence) + 0.03
                )
                existing.source = source or existing.source
                changed.append(existing)
                continue

            fact = RelationshipFact(
                fact=normalized,
                normalized_fact=normalized.lower(),
                tags=tags,
                confidence=confidence,
                first_confirmed=today,
                last_confirmed=today,
                confirmations=1,
                source=source,
            )
            store.facts.append(fact)
            by_norm[fact.normalized_fact] = fact
            changed.append(fact)

        if changed:
            self._save(store)
        return changed

    def list_facts(self) -> List[RelationshipFact]:
        store = self._load()
        return store.facts

    def delete_fact(self, fact: str) -> bool:
        normalized = _normalize_fact(fact).lower()
        if not normalized:
            return False
        store = self._load()
        before = len(store.facts)
        store.facts = [f for f in store.facts if f.normalized_fact != normalized]
        if len(store.facts) < before:
            self._save(store)
            return True
        return False

    def search(
        self,
        query: str,
        k: int = 4,
        min_confidence: float = 0.55,
    ) -> List[RelationshipFact]:
        store = self._load()
        if not store.facts:
            return []

        safe_k = max(1, int(k))
        query = (query or "").strip().lower()
        query_tokens = {t for t in re.findall(r"[a-z0-9_]+", query) if len(t) > 2}

        scored: List[tuple[float, RelationshipFact]] = []
        for fact in store.facts:
            if fact.confidence < min_confidence:
                continue
            fact_text = fact.fact.lower()
            fact_tokens = {t for t in re.findall(r"[a-z0-9_]+", fact_text) if len(t) > 2}
            tag_tokens = {t.lower() for t in fact.tags}

            score = fact.confidence * 2.0
            if query:
                if query in fact_text:
                    score += 2.5
                overlap = len(query_tokens & fact_tokens)
                score += overlap * 0.35
                score += len(query_tokens & tag_tokens) * 0.5
            # Slight recency bump.
            if fact.last_confirmed == date.today().isoformat():
                score += 0.15

            if score > 0:
                scored.append((score, fact))

        scored.sort(
            key=lambda x: (x[0], x[1].confidence, x[1].last_confirmed),
            reverse=True,
        )
        return [f for _, f in scored[:safe_k]]

    def to_context_block(self, query: str, k: int = 4) -> str:
        facts = self.search(query=query, k=k)
        if not facts:
            return ""
        lines = ["--- RELATIONSHIP MEMORY (HIGH PRIORITY) ---"]
        for fact in facts:
            tags = ", ".join(fact.tags) if fact.tags else "user_profile"
            lines.append(
                f"- {fact.fact} [tags: {tags}; confidence: {fact.confidence:.2f}; last_confirmed: {fact.last_confirmed}]"
            )
        lines.append("--- END RELATIONSHIP MEMORY ---")
        return "\n".join(lines)
