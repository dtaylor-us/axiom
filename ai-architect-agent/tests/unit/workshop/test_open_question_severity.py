"""Tests for architectural impact on information gaps."""

from app.workshop.context import InformationGap


def test_information_gap_has_architectural_impact_field() -> None:
    gap = InformationGap(
        gap_id="GAP-1",
        category="usage_context",
        description="Uptime target is missing",
    )

    assert hasattr(gap, "architectural_impact")


def test_architectural_impact_defaults_to_informational() -> None:
    gap = InformationGap(
        gap_id="GAP-1",
        category="usage_context",
        description="Current metric baseline is missing",
    )

    assert gap.architectural_impact == "informational"


def test_architectural_impact_accepts_blocks_attribute_confirmation() -> None:
    gap = InformationGap(
        gap_id="GAP-1",
        category="usage_context",
        description="Availability SLA is missing",
        architectural_impact="blocks_attribute_confirmation",
        confidence_impact=0.4,
    )

    assert gap.architectural_impact == "blocks_attribute_confirmation"
    assert gap.confidence_impact == 0.4
