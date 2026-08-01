"""
Unit tests for utility tree generation.

Tests verify the has_sufficient_for_utility_tree threshold, UtilityTreeGenerator
LLM call behaviour, and UtilityTree model validation.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.workshop.context import (
    WorkshopScenario,
    UtilityTree,
    UtilityTreeNode,
    WorkshopContext,
)
from app.workshop.utility_tree_generator import UtilityTreeGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scenario(sid: str, completeness: str, attrs: list[str]) -> WorkshopScenario:
    measure = "p99 < 200ms" if completeness == "complete" else ""
    return WorkshopScenario(
        scenario_id=sid,
        title=f"Scenario {sid}",
        stimulus=f"event {sid} occurs that stresses the system",
        source="external user traffic",
        environment="production peak hours",
        artifact="order processing service",
        response="the system responds without degradation",
        response_measure=measure,
        exercises_attributes=attrs,
    )


def _ctx(scenarios: list[QAScenario]) -> WorkshopContext:
    return WorkshopContext(
        session_id="s-1",
        user_id="u-1",
        system_name="Trade Platform",
        scenarios=scenarios,
    )


def _valid_tree_json(generated_at_turn: int = 5) -> str:
    return json.dumps({
        "generated_at_turn": generated_at_turn,
        "total_scenarios": 5,
        "architectural_drivers": ["sc-1"],
        "nodes": [
            {
                "node_id": "n-1",
                "attribute_name": "Performance",
                "refinement": "Latency",
                "scenario_id": "sc-1",
                "scenario_title": "High load",
                "business_importance": "H",
                "technical_risk": "H",
                "priority_label": "(H,H)",
                "rationale": "Critical path",
            }
        ],
        "generation_rationale": "Sufficient scenarios across 3 attributes.",
    })


# ---------------------------------------------------------------------------
# has_sufficient_for_utility_tree threshold tests
# ---------------------------------------------------------------------------

class TestHasSufficientForUtilityTree:
    def test_false_with_too_few_scenarios(self):
        # 4 scenarios across 3 attributes — below 5-scenario threshold
        scenarios = [
            _scenario(f"sc-{i}", "complete", [f"attr-{i % 3}"])
            for i in range(4)
        ]
        ctx = _ctx(scenarios)
        assert ctx.has_sufficient_for_utility_tree is False

    def test_false_with_too_few_attributes(self):
        # 5 scenarios but only 2 distinct attributes
        scenarios = [
            _scenario(f"sc-{i}", "complete", ["perf", "avail"])
            for i in range(5)
        ]
        ctx = _ctx(scenarios)
        assert ctx.has_sufficient_for_utility_tree is False

    def test_true_at_threshold(self):
        # Exactly 5 scenarios across exactly 3 distinct attributes
        scenarios = [
            _scenario("sc-0", "complete", ["perf"]),
            _scenario("sc-1", "partial", ["avail"]),
            _scenario("sc-2", "needs_measure", ["security"]),
            _scenario("sc-3", "complete", ["perf"]),
            _scenario("sc-4", "partial", ["avail"]),
        ]
        ctx = _ctx(scenarios)
        assert ctx.has_sufficient_for_utility_tree is True

    def test_aspirational_scenarios_do_not_count(self):
        # Short content computes as aspirational — should not contribute to threshold.
        # 3 aspirational + 2 complete across only 2 attributes: threshold not met.
        scenarios = [
            WorkshopScenario(scenario_id="sc-0", title="vague", exercises_attributes=["perf"]),
            WorkshopScenario(scenario_id="sc-1", title="vague", exercises_attributes=["avail"]),
            WorkshopScenario(scenario_id="sc-2", title="vague", exercises_attributes=["security"]),
            _scenario("sc-3", "complete", ["perf"]),
            _scenario("sc-4", "complete", ["avail"]),
        ]
        ctx = _ctx(scenarios)
        # 3 aspirational + 2 complete → only 2 "real" scenarios across 2 attributes
        assert ctx.has_sufficient_for_utility_tree is False


# ---------------------------------------------------------------------------
# UtilityTreeGenerator tests
# ---------------------------------------------------------------------------

class TestUtilityTreeGenerator:
    def test_generate_returns_none_when_threshold_not_met(self):
        """Generator must skip LLM call and return None when threshold is not met."""
        llm = AsyncMock()
        gen = UtilityTreeGenerator(llm)

        ctx = _ctx([_scenario("sc-1", "complete", ["perf"])])  # only 1 scenario

        result = asyncio.run(gen.generate(ctx))

        assert result is None
        llm.complete.assert_not_called()

    def test_generate_calls_llm_when_sufficient(self):
        """Generator must call LLM when threshold is met."""
        llm = AsyncMock()
        llm.complete = AsyncMock(return_value=_valid_tree_json())
        gen = UtilityTreeGenerator(llm)

        scenarios = [
            _scenario("sc-0", "complete", ["perf"]),
            _scenario("sc-1", "partial", ["avail"]),
            _scenario("sc-2", "needs_measure", ["security"]),
            _scenario("sc-3", "complete", ["perf"]),
            _scenario("sc-4", "partial", ["avail"]),
        ]
        ctx = _ctx(scenarios)

        result = asyncio.run(gen.generate(ctx))

        llm.complete.assert_called_once()
        assert result is not None
        assert result.total_scenarios == 5

    def test_generate_returns_existing_tree_on_llm_failure(self):
        """Generator must return existing utility_tree when LLM raises an exception."""
        existing_tree = UtilityTree(
            generated_at_turn=3,
            total_scenarios=5,
            architectural_drivers=[],
            nodes=[],
            generation_rationale="previous run",
        )
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        gen = UtilityTreeGenerator(llm)

        scenarios = [
            _scenario("sc-0", "complete", ["perf"]),
            _scenario("sc-1", "partial", ["avail"]),
            _scenario("sc-2", "needs_measure", ["security"]),
            _scenario("sc-3", "complete", ["perf"]),
            _scenario("sc-4", "partial", ["avail"]),
        ]
        ctx = _ctx(scenarios)
        ctx = ctx.model_copy(update={"utility_tree": existing_tree})

        result = asyncio.run(gen.generate(ctx))

        assert result is existing_tree


# ---------------------------------------------------------------------------
# UtilityTreeNode model validation
# ---------------------------------------------------------------------------

class TestUtilityTreeNodeModel:
    def test_utility_tree_node_validates(self):
        node = UtilityTreeNode(
            node_id="n-1",
            attribute_name="Performance",
            refinement="Latency",
            scenario_id="sc-1",
            scenario_title="High load",
            business_importance="H",
            technical_risk="H",
            priority_label="(H,H)",
            rationale="Critical path",
        )
        assert node.priority_label == "(H,H)"
        assert node.business_importance == "H"

    def test_utility_tree_aggregates_nodes(self):
        node = UtilityTreeNode(
            node_id="n-1",
            attribute_name="Performance",
            refinement="Latency",
            scenario_id="sc-1",
            scenario_title="High load",
            business_importance="H",
            technical_risk="M",
            priority_label="(H,M)",
            rationale="",
        )
        tree = UtilityTree(
            generated_at_turn=5,
            total_scenarios=1,
            architectural_drivers=["sc-1"],
            nodes=[node],
            generation_rationale="test",
        )
        assert len(tree.nodes) == 1
        assert tree.architectural_drivers == ["sc-1"]


# ---------------------------------------------------------------------------
# generate_utility_tree_node staleness tests
# ---------------------------------------------------------------------------

class TestGenerateUtilityTreeNodeStaleness:
    """
    Verify that the node skips the LLM when the utility tree is still current
    (i.e. the eligible scenario count has not changed since last generation).
    """

    def _make_config(self, generator):
        return {"configurable": {"utility_generator": generator}}

    def test_skips_llm_when_tree_is_current(self):
        """Node must not call LLM when tree total_scenarios matches eligible count."""
        from app.workshop.nodes import generate_utility_tree_node

        existing_tree = UtilityTree(
            generated_at_turn=4,
            total_scenarios=5,  # matches the 5 eligible scenarios below
            architectural_drivers=["sc-1"],
            nodes=[],
            generation_rationale="previous run",
        )
        scenarios = [
            _scenario(f"sc-{i}", "complete", [f"attr-{i % 3}"])
            for i in range(5)
        ]
        ctx = _ctx(scenarios)
        ctx = ctx.model_copy(update={"utility_tree": existing_tree})

        generator = AsyncMock()
        result = asyncio.run(
            generate_utility_tree_node(ctx, self._make_config(generator))
        )

        # Tree is current — generator must not be called and state must be unchanged.
        generator.generate.assert_not_called()
        assert result.utility_tree is existing_tree

    def test_calls_llm_when_new_scenario_added(self):
        """Node must call the generator when eligible count exceeds tree total_scenarios."""
        from app.workshop.nodes import generate_utility_tree_node

        existing_tree = UtilityTree(
            generated_at_turn=4,
            total_scenarios=5,  # tree was built from 5 scenarios
            architectural_drivers=["sc-1"],
            nodes=[],
            generation_rationale="previous run",
        )
        # 6 eligible scenarios now — count increased
        scenarios = [
            _scenario(f"sc-{i}", "complete", [f"attr-{i % 3}"])
            for i in range(6)
        ]
        ctx = _ctx(scenarios)
        ctx = ctx.model_copy(update={"utility_tree": existing_tree, "current_turn": 5})

        new_tree = UtilityTree(
            generated_at_turn=5,
            total_scenarios=6,
            architectural_drivers=["sc-1"],
            nodes=[],
            generation_rationale="updated",
        )
        generator = AsyncMock()
        generator.generate = AsyncMock(return_value=new_tree)

        result = asyncio.run(
            generate_utility_tree_node(ctx, self._make_config(generator))
        )

        generator.generate.assert_called_once()
        assert result.utility_tree is new_tree
