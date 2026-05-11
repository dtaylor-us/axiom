"""ADL-041: scenario elicitation precedes attribute inference in the workshop graph."""

from __future__ import annotations

from pathlib import Path


def test_scenario_before_attributes() -> None:
    """elicit_scenarios must appear before infer_attributes_from_scenarios in agent.py."""
    agent_py = Path(__file__).resolve().parents[3] / "app" / "workshop" / "agent.py"
    text = agent_py.read_text(encoding="utf-8")
    pos_scenario = text.find('"elicit_scenarios"')
    pos_infer = text.find('"infer_attributes_from_scenarios"')
    assert pos_scenario != -1, "elicit_scenarios node missing from agent.py"
    assert pos_infer != -1, "infer_attributes_from_scenarios node missing from agent.py"
    assert pos_scenario < pos_infer, (
        "ADL-041: elicit_scenarios must be declared before infer_attributes_from_scenarios"
    )
