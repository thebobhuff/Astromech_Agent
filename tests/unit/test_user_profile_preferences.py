from pathlib import Path

from app.core.user_profile import (
    extract_preference_candidates,
    extract_durable_user_facts,
    evaluate_and_update_user_preferences,
)
from app.memory.relationship_memory import RelationshipMemoryStore


def test_extract_preference_candidates_filters_task_requests():
    prompt = (
        "I prefer concise answers. "
        "Can you write a script for me? "
        "I'm into TypeScript. "
        "I need you to fix this bug."
    )
    items = extract_preference_candidates(prompt)
    assert "I prefer concise answers" in items
    assert "I'm into TypeScript" in items
    assert all("need you to" not in x.lower() for x in items)


def test_evaluate_and_update_user_preferences_adds_under_preferences(tmp_path: Path):
    user_file = tmp_path / "USER.md"
    relationship_file = tmp_path / "relationship.json"
    relationship_store = RelationshipMemoryStore(str(relationship_file))
    user_file.write_text(
        "# User Profile\n\n- **Name**: Test User\n- **Role**: Developer\n- **Preferences**:\n    - (To be learned)\n",
        encoding="utf-8",
    )

    evaluate_and_update_user_preferences(
        "I like dark roast coffee. I'm into Python.",
        user_file=str(user_file),
        relationship_store=relationship_store,
    )

    content = user_file.read_text(encoding="utf-8")
    assert "- **Preferences**:" in content
    assert "    - I like dark roast coffee" in content
    assert "    - I'm into Python" in content
    assert "(To be learned)" not in content

    facts = relationship_store.list_facts()
    assert len(facts) >= 2
    assert any("dark roast coffee" in f.fact.lower() for f in facts)
    assert any("python" in f.fact.lower() for f in facts)
    assert all(f.last_confirmed for f in facts)
    assert all(0.0 <= f.confidence <= 1.0 for f in facts)


def test_extract_durable_user_facts_tags_communication_style():
    facts = extract_durable_user_facts("I prefer concise bullet points and direct answers.")
    assert facts
    tags = set(facts[0].tags)
    assert "communication_style" in tags
    assert "preference" in tags
