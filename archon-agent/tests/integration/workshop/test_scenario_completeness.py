"""
Integration-style checks for QAScenario completeness invariants (also enforced at unit level).
"""

from __future__ import annotations

from app.workshop.context import QAScenario


def test_empty_scenario_always_aspirational() -> None:
    """Creates a QAScenario with completeness='complete' and empty fields — recomputed."""
    scenario = QAScenario(
        scenario_id="SC-TEST",
        stimulus="",
        source="",
        environment="",
        artifact="",
        response="",
        response_measure="",
        completeness="complete",
    )
    assert scenario.completeness == "aspirational", (
        "Empty scenario must never be marked complete. "
        f"Got: {scenario.completeness}"
    )


def test_partial_scenario_not_complete() -> None:
    scenario = QAScenario(
        scenario_id="SC-TEST",
        stimulus="System receives 10,000 concurrent requests",
        source="",
        environment="",
        artifact="",
        response="System scales horizontally",
        response_measure="",
        completeness="complete",
    )
    assert scenario.completeness == "needs_measure"


def test_complete_scenario_requires_all_key_fields() -> None:
    scenario = QAScenario(
        scenario_id="SC-TEST",
        stimulus="AKS node fails during seasonal processing",
        source="operations",
        environment="Peak seasonal accreditation window",
        artifact="compute",
        response="System isolates failed workset and resumes",
        response_measure="Recovery within 15 minutes, no lineage loss",
        completeness="aspirational",
    )
    assert scenario.completeness == "complete"
