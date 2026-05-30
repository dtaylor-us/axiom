"""ADL-043: resolve_questions wired between reconcile_gaps and elicit_scenarios."""

from __future__ import annotations

from pathlib import Path


def test_resolver_wired_in_graph() -> None:
    agent_py = Path(__file__).resolve().parents[3] / "app" / "workshop" / "agent.py"
    text = agent_py.read_text(encoding="utf-8")
    assert 'add_node("resolve_questions"' in text
    assert 'add_edge("reconcile_gaps", "resolve_questions")' in text
    assert 'add_edge("resolve_questions", "elicit_scenarios")' in text
