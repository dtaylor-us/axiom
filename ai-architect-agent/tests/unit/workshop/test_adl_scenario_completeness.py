"""ADL-042: QAScenario completeness is derived from fields, not LLM self-report."""

from __future__ import annotations

from app.workshop.context import QAScenario


def test_empty_scenario_not_complete() -> None:
    """LLM cannot mark an empty scenario complete — post-init recomputes completeness."""
    sc = QAScenario(
        scenario_id="SC-X",
        completeness="complete",
        stimulus="",
        response="",
        response_measure="",
    )
    assert sc.completeness == "aspirational"
