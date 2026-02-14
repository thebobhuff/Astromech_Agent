from pathlib import Path

from app.memory.relationship_memory import RelationshipFactInput, RelationshipMemoryStore


def test_relationship_memory_upsert_and_search(tmp_path: Path):
    store = RelationshipMemoryStore(str(tmp_path / "relationship.json"))

    store.upsert_facts(
        [
            RelationshipFactInput(
                fact="I prefer concise responses.",
                tags=["preference", "communication_style"],
                confidence=0.85,
            ),
            RelationshipFactInput(
                fact="I'm working on Astromech every week.",
                tags=["recurring_project", "habit"],
                confidence=0.82,
            ),
        ]
    )

    results = store.search("concise style", k=3)
    assert results
    assert "concise" in results[0].fact.lower()
    assert "communication_style" in results[0].tags


def test_relationship_memory_reconfirmation_increases_confirmations(tmp_path: Path):
    store = RelationshipMemoryStore(str(tmp_path / "relationship.json"))
    store.upsert_facts(
        [RelationshipFactInput(fact="I prefer short answers.", tags=["preference"], confidence=0.7)]
    )
    store.upsert_facts(
        [RelationshipFactInput(fact="I prefer short answers", tags=["communication_style"], confidence=0.75)]
    )

    facts = store.list_facts()
    assert len(facts) == 1
    fact = facts[0]
    assert fact.confirmations >= 2
    assert "communication_style" in fact.tags
