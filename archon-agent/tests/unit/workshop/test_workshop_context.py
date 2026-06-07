"""Unit tests for WorkshopContext Pydantic models."""
import pytest
from app.workshop.context import (
    WorkshopContext,
    ElicitedAttribute,
    InformationGap,
    QAScenario,
)


def _make_context(**overrides) -> WorkshopContext:
    defaults = dict(
        session_id="test-session",
        user_id="user-1",
        system_name="Payment Service",
    )
    defaults.update(overrides)
    return WorkshopContext(**defaults)


def _scenario_complete(sid: str = "sc-1") -> QAScenario:
    return QAScenario(
        scenario_id=sid,
        stimulus="load spike",
        source="load balancer",
        environment="production",
        artifact="svc",
        response="serve requests",
        response_measure="p99 < 200 ms",
        completeness="complete",
    )


def _confirmed_elicited(aid: str, name: str, scenario: QAScenario | None) -> ElicitedAttribute:
    scenarios = [scenario] if scenario else []
    return ElicitedAttribute(
        attribute_id=aid,
        name=name,
        category="performance",
        description="d",
        confidence="confirmed",
        scenarios=scenarios,
    )


class TestGapCompletion:
    def test_zero_when_no_gaps(self):
        ctx = _make_context()
        assert ctx.gap_completion_pct == 0

    def test_full_when_all_filled(self):
        ctx = _make_context(
            gaps=[
                InformationGap(
                    gap_id="g1",
                    category="business_context",
                    description="x",
                    filled=True,
                ),
                InformationGap(
                    gap_id="g2",
                    category="usage_context",
                    description="y",
                    filled=True,
                ),
            ],
        )
        assert ctx.gap_completion_pct == 100

    def test_partial_completion(self):
        ctx = _make_context(
            gaps=[
                InformationGap(
                    gap_id="g1",
                    category="business_context",
                    description="x",
                    filled=True,
                ),
                InformationGap(
                    gap_id="g2",
                    category="usage_context",
                    description="y",
                    filled=False,
                ),
            ],
        )
        assert ctx.gap_completion_pct == 50

    def test_total_and_filled_counts(self):
        ctx = _make_context(
            gaps=[
                InformationGap(
                    gap_id="g1",
                    category="business_context",
                    description="a",
                    filled=True,
                ),
                InformationGap(
                    gap_id="g2",
                    category="business_context",
                    description="b",
                    filled=False,
                ),
                InformationGap(
                    gap_id="g3",
                    category="usage_context",
                    description="c",
                    filled=True,
                ),
            ],
        )
        assert ctx.total_gaps == 3
        assert ctx.filled_gaps == 2


class TestConfirmedAttributeCount:
    def test_zero_when_none(self):
        ctx = _make_context()
        assert ctx.confirmed_attribute_count == 0

    def test_counts_only_confirmed_ids(self):
        ctx = _make_context(
            confirmed_attributes=["QA-1"],
            attributes=[
                _confirmed_elicited("QA-1", "perf", _scenario_complete()),
                ElicitedAttribute(
                    attribute_id="QA-2",
                    name="security",
                    category="security",
                    description="d",
                    confidence="inferred",
                ),
            ],
        )
        assert ctx.confirmed_attribute_count == 1


class TestHasSufficientAttributes:
    def test_false_when_fewer_than_three_confirmed(self):
        ctx = _make_context(
            confirmed_attributes=["QA-1", "QA-2"],
            attributes=[
                _confirmed_elicited("QA-1", "perf", _scenario_complete("s1")),
                _confirmed_elicited("QA-2", "security", _scenario_complete("s2")),
            ],
        )
        assert ctx.has_sufficient_attributes is False

    def test_false_when_confirmed_but_missing_scenario(self):
        ctx = _make_context(
            confirmed_attributes=["QA-1", "QA-2", "QA-3"],
            attributes=[
                _confirmed_elicited("QA-1", "perf", _scenario_complete()),
                _confirmed_elicited("QA-2", "security", _scenario_complete()),
                _confirmed_elicited("QA-3", "avail", None),
            ],
        )
        assert ctx.has_sufficient_attributes is False

    def test_false_when_scenario_is_aspirational(self):
        scen = QAScenario(
            scenario_id="x",
            completeness="aspirational",
        )
        ctx = _make_context(
            confirmed_attributes=["QA-1", "QA-2", "QA-3"],
            attributes=[
                _confirmed_elicited("QA-1", "perf", scen),
                _confirmed_elicited("QA-2", "security", _scenario_complete("s2")),
                _confirmed_elicited("QA-3", "avail", _scenario_complete("s3")),
            ],
        )
        assert ctx.has_sufficient_attributes is False

    def test_true_when_three_confirmed_with_non_aspirational_scenarios(self):
        ctx = _make_context(
            confirmed_attributes=["QA-1", "QA-2", "QA-3"],
            attributes=[
                _confirmed_elicited("QA-1", "perf", _scenario_complete("s1")),
                _confirmed_elicited("QA-2", "security", _scenario_complete("s2")),
                _confirmed_elicited("QA-3", "availability", _scenario_complete("s3")),
            ],
        )
        assert ctx.has_sufficient_attributes is True
