"""
Unit tests for architecture implication synthesis.

Tests verify the ImplicationSynthesiser LLM call behaviour,
guard conditions, and ArchitectureImplication model constraints.
"""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock

import pytest

from app.workshop.context import (
    ArchitectureImplication,
    UtilityTree,
    UtilityTreeNode,
    WorkshopContext,
    WorkshopScenario,
)
from app.workshop.implication_synthesiser import (
    PROHIBITED_MECHANISM_TERMS,
    ImplicationSynthesiser,
)

# Maximum implications the synthesiser must not exceed (mirrors the constant in
# implication_synthesiser.py — duplicated here so the test is self-contained).
MAX_IMPLICATIONS = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(scenario_id: str, business_importance: str = "H", technical_risk: str = "H") -> UtilityTreeNode:
    return UtilityTreeNode(
        node_id=f"n-{scenario_id}",
        attribute_name="Performance",
        refinement="Latency",
        scenario_id=scenario_id,
        scenario_title=f"Scenario {scenario_id}",
        business_importance=business_importance,
        technical_risk=technical_risk,
        priority_label=f"({business_importance},{technical_risk})",
        rationale="",
    )


def _tree(driver_ids: list[str], nodes: list[UtilityTreeNode] | None = None) -> UtilityTree:
    if nodes is None:
        nodes = [_node(d) for d in driver_ids]
    return UtilityTree(
        generated_at_turn=5,
        total_scenarios=len(driver_ids),
        architectural_drivers=driver_ids,
        nodes=nodes,
        generation_rationale="test",
    )


def _scenario(scenario_id: str) -> WorkshopScenario:
    return WorkshopScenario(
        scenario_id=scenario_id,
        title=f"Scenario {scenario_id}",
        stimulus="an event occurs that stresses the system under peak load",
        source="external user traffic surge",
        environment="production at peak hours",
        artifact="order processing service",
        response="the system processes requests without degradation",
        response_measure="p99 latency < 200ms",
        exercises_attributes=["performance"],
    )


def _ctx(
    utility_tree: UtilityTree | None = None,
    scenario_ids: list[str] | None = None,
) -> WorkshopContext:
    scenarios = [_scenario(sid) for sid in (scenario_ids or [])]
    return WorkshopContext(
        session_id="s-1",
        user_id="u-1",
        system_name="Trade Platform",
        utility_tree=utility_tree,
        scenarios=scenarios,
    )


def _implication_json(
    implication_id: str = "impl-1",
    scenario_id: str = "sc-1",
    strength: str = "must",
    implication: str | None = None,
) -> dict:
    return {
        "implication_id": implication_id,
        "source_scenario_id": scenario_id,
        "source_scenario_title": f"Scenario {scenario_id}",
        "implication": implication or (
            f"Because {scenario_id} occurs under peak load, "
            f"task processing latency must remain below the specified target."
        ),
        "tradeoff": (
            "Tradeoff: this requirement prioritises performance over cost "
            "because extra operational headroom may be necessary."
        ),
        "affected_quality_attrs": ["Performance", "Availability"],
        "constraint_type": "performance",
        "strength": strength,
        "measurable_condition": "p99 latency < 200ms",
    }


def _valid_response_json(n: int = 2) -> str:
    return json.dumps({
        "implications": [_implication_json(f"impl-{i}", f"sc-{i}") for i in range(n)],
        "synthesis_summary": "Two structural constraints derived.",
    })


# ---------------------------------------------------------------------------
# ImplicationSynthesiser tests
# ---------------------------------------------------------------------------

class TestSynthesiseReturnsEmptyWhenNoTree:
    def test_synthesise_returns_empty_when_no_tree(self):
        """Must return empty list without calling LLM when utility_tree is None."""
        llm = AsyncMock()
        synthesiser = ImplicationSynthesiser(llm)
        ctx = _ctx(utility_tree=None, scenario_ids=[])

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(synthesiser.synthesise(ctx))

        assert result == []
        llm.complete.assert_not_called()


class TestSynthesiseExtractsDriverScenarios:
    def test_synthesise_calls_llm_with_driver_scenarios(self):
        """Synthesiser must call LLM when utility_tree and driver scenarios are present."""
        llm = AsyncMock()
        llm.complete = AsyncMock(return_value=_valid_response_json(2))
        synthesiser = ImplicationSynthesiser(llm)

        tree = _tree(["sc-1", "sc-2"])
        # Provide matching scenarios so driver lookup succeeds
        ctx = _ctx(utility_tree=tree, scenario_ids=["sc-1", "sc-2"])

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(synthesiser.synthesise(ctx))

        llm.complete.assert_called_once()
        assert len(result) == 2

    def test_synthesise_returns_existing_on_llm_failure(self):
        """Must return existing implications when LLM raises."""
        existing = [
            ArchitectureImplication(
                implication_id="impl-old",
                source_scenario_id="sc-0",
                source_scenario_title="old scenario",
                implication=(
                    "Because sc-0 occurs during load spikes, response latency "
                    "must remain within the stated service target."
                ),
                tradeoff="Tradeoff: this requirement prioritises performance over cost.",
                affected_quality_attrs=["Performance"],
                constraint_type="performance",
                strength="must",
                measurable_condition="p99 latency < 200ms",
            )
        ]
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("LLM down"))
        synthesiser = ImplicationSynthesiser(llm)

        tree = _tree(["sc-0"])
        ctx = _ctx(utility_tree=tree, scenario_ids=["sc-0"])
        ctx = ctx.model_copy(update={"architecture_implications": existing})

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(synthesiser.synthesise(ctx))

        assert result == existing


class TestImplicationMaxGuard:
    def test_max_implications_guard(self):
        """Synthesiser must trim result to MAX_IMPLICATIONS entries."""
        # LLM returns more than MAX_IMPLICATIONS — synthesiser must trim
        many_implications = [_implication_json(f"impl-{i}", f"sc-{i}") for i in range(MAX_IMPLICATIONS + 5)]
        response = json.dumps({"implications": many_implications, "synthesis_summary": "many"})

        llm = AsyncMock()
        llm.complete = AsyncMock(return_value=response)
        synthesiser = ImplicationSynthesiser(llm)

        tree = _tree([f"sc-{i}" for i in range(5)])
        ctx = _ctx(utility_tree=tree, scenario_ids=[f"sc-{i}" for i in range(5)])

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(synthesiser.synthesise(ctx))

        assert len(result) <= MAX_IMPLICATIONS


class TestMechanismProhibition:
    def test_synthesise_does_not_produce_consensus_protocol(self):
        """Clean synthesis output must not contain consensus protocol."""
        result = self._synthesise_from_response(_valid_response_json(1))

        assert "consensus protocol" not in result[0].implication.lower()

    def test_synthesise_does_not_produce_circuit_breaker(self):
        """Clean synthesis output must not contain circuit breaker."""
        result = self._synthesise_from_response(_valid_response_json(1))

        assert "circuit breaker" not in result[0].implication.lower()

    def test_synthesise_does_not_produce_async_worker_pool(self):
        """Clean synthesis output must not contain async worker pool."""
        result = self._synthesise_from_response(_valid_response_json(1))

        assert "async worker pool" not in result[0].implication.lower()

    def test_synthesise_does_not_produce_any_prohibited_mechanism_name(self):
        """Clean synthesis output must avoid every prohibited mechanism term."""
        result = self._synthesise_from_response(_valid_response_json(1))
        text = result[0].implication.lower()

        assert all(term not in text for term in PROHIBITED_MECHANISM_TERMS)

    def test_validate_implication_returns_warning_for_mechanism_terms(self):
        """Validator must flag prohibited mechanism terms without rejecting."""
        synthesiser = ImplicationSynthesiser(AsyncMock())
        implication = self._implication_with_text(
            "Because failures occur, task flow must include a consensus protocol."
        )

        warning = synthesiser._validate_implication(implication)

        assert warning is not None
        assert "consensus protocol" in warning

    def test_validate_implication_returns_none_for_clean_requirements(self):
        """Validator must accept requirement language that names no mechanism."""
        synthesiser = ImplicationSynthesiser(AsyncMock())
        implication = self._implication_with_text(
            "Because failures occur, task flow must remain consistent."
        )

        warning = synthesiser._validate_implication(implication)

        assert warning is None

    def test_synthesise_logs_warning_when_mechanism_terms_found(self, caplog):
        """Synthesiser must log a warning when a kept implication names mechanisms."""
        response = json.dumps({
            "implications": [
                _implication_json(
                    implication=(
                        "Because failures occur, task flow must include a "
                        "circuit breaker."
                    )
                )
            ],
            "synthesis_summary": "Mechanism violation for test.",
        })

        with caplog.at_level(logging.WARNING):
            self._synthesise_from_response(response)

        assert "IMPLICATION_MECHANISM_VIOLATION" in caplog.text
        assert "circuit breaker" in caplog.text

    def test_every_implication_has_non_empty_tradeoff_field(self):
        """Synthesised implications must carry tradeoff guidance."""
        result = self._synthesise_from_response(_valid_response_json(2))

        assert all(imp.tradeoff for imp in result)

    def test_every_implication_has_measurable_condition_field(self):
        """Synthesised implications must carry a measurable condition."""
        result = self._synthesise_from_response(_valid_response_json(2))

        assert all(imp.measurable_condition for imp in result)

    def _synthesise_from_response(
        self, response: str
    ) -> list[ArchitectureImplication]:
        import asyncio

        llm = AsyncMock()
        llm.complete = AsyncMock(return_value=response)
        synthesiser = ImplicationSynthesiser(llm)
        ctx = _ctx(utility_tree=_tree(["sc-1"]), scenario_ids=["sc-1"])

        return asyncio.get_event_loop().run_until_complete(
            synthesiser.synthesise(ctx)
        )

    def _implication_with_text(self, text: str) -> ArchitectureImplication:
        return ArchitectureImplication(
            implication_id="impl-1",
            source_scenario_id="sc-1",
            source_scenario_title="Scenario sc-1",
            implication=text,
            tradeoff="Tradeoff: this requirement prioritises safety over throughput.",
            affected_quality_attrs=["Safety"],
            constraint_type="safety",
            strength="must",
            measurable_condition="halt within 100ms",
        )


class TestImplicationModel:
    def test_implication_model_validates(self):
        impl = ArchitectureImplication(
            implication_id="impl-1",
            source_scenario_id="sc-1",
            source_scenario_title="Load spike",
            implication=(
                "Because a load spike can saturate ingress capacity, "
                "request handling must remain within the stated latency target."
            ),
            tradeoff="Tradeoff: this requirement prioritises performance over cost.",
            affected_quality_attrs=["Performance", "Availability"],
            constraint_type="performance",
            strength="must",
            measurable_condition="p99 latency < 200ms",
        )
        assert impl.strength == "must"
        assert impl.constraint_type == "performance"

    def test_implication_strength_values(self):
        for strength in ("must", "should", "may"):
            impl = ArchitectureImplication(
                implication_id="i",
                source_scenario_id="s",
                source_scenario_title="t",
                implication="Because x occurs, operational continuity must be preserved.",
                tradeoff="Tradeoff: this requirement prioritises continuity over cost.",
                affected_quality_attrs=["Operational Continuity"],
                constraint_type="operational",
                strength=strength,
                measurable_condition="qualitative continuity target",
            )
            assert impl.strength == strength


# ---------------------------------------------------------------------------
# synthesise_implications_node staleness tests
# ---------------------------------------------------------------------------

class TestSynthesiseImplicationsNodeStaleness:
    """
    Verify that the node skips the LLM when the utility tree has not been
    regenerated since the last synthesis run.
    """

    def _make_config(self, synthesiser):
        return {"configurable": {"implication_synthesiser": synthesiser}}

    def test_skips_llm_when_tree_unchanged_and_implications_exist(self):
        """
        Node must not call LLM when the tree was generated in a prior turn
        and there are already implications.
        """
        import asyncio
        from app.workshop.nodes import synthesise_implications_node

        # Tree was generated in turn 4; current turn is 5 → tree not regenerated this turn.
        tree = UtilityTree(
            generated_at_turn=4,
            total_scenarios=3,
            architectural_drivers=["sc-1"],
            nodes=[],
            generation_rationale="previous",
        )
        existing_impl = ArchitectureImplication(
            implication_id="impl-1",
            source_scenario_id="sc-1",
            source_scenario_title="Load spike",
            implication=(
                "Because sc-1 occurs under peak load, response latency must "
                "remain within the defined target."
            ),
            tradeoff="Tradeoff: this requirement prioritises performance over cost.",
            affected_quality_attrs=["Performance"],
            constraint_type="performance",
            strength="must",
            measurable_condition="p99 latency < 200ms",
        )
        ctx = _ctx(utility_tree=tree)
        ctx = ctx.model_copy(update={
            "architecture_implications": [existing_impl],
            "current_turn": 5,
        })

        synthesiser = AsyncMock()
        result = asyncio.get_event_loop().run_until_complete(
            synthesise_implications_node(ctx, self._make_config(synthesiser))
        )

        # Synthesiser must not be called — implications are still current.
        synthesiser.synthesise.assert_not_called()
        assert result.architecture_implications == [existing_impl]

    def test_calls_llm_when_tree_regenerated_this_turn(self):
        """
        Node must call LLM when the tree was regenerated in the current turn,
        even if implications already exist from the previous tree.
        """
        import asyncio
        from app.workshop.nodes import synthesise_implications_node

        # Tree was just regenerated this turn (turn 5).
        tree = UtilityTree(
            generated_at_turn=5,
            total_scenarios=4,
            architectural_drivers=["sc-1", "sc-2"],
            nodes=[_node("sc-1"), _node("sc-2")],
            generation_rationale="updated this turn",
        )
        ctx = _ctx(utility_tree=tree, scenario_ids=["sc-1", "sc-2"])
        ctx = ctx.model_copy(update={"current_turn": 5})

        synthesiser = AsyncMock()
        synthesiser.synthesise = AsyncMock(return_value=[])

        asyncio.get_event_loop().run_until_complete(
            synthesise_implications_node(ctx, self._make_config(synthesiser))
        )

        synthesiser.synthesise.assert_called_once()

    def test_calls_llm_when_no_implications_yet(self):
        """
        Node must call LLM when there are no implications yet, even if the
        tree was generated in a prior turn.
        """
        import asyncio
        from app.workshop.nodes import synthesise_implications_node

        # Tree was generated in turn 3; current turn is 6 — but no implications yet.
        tree = UtilityTree(
            generated_at_turn=3,
            total_scenarios=5,
            architectural_drivers=["sc-1"],
            nodes=[_node("sc-1")],
            generation_rationale="first tree",
        )
        ctx = _ctx(utility_tree=tree, scenario_ids=["sc-1"])
        ctx = ctx.model_copy(update={"current_turn": 6, "architecture_implications": []})

        synthesiser = AsyncMock()
        synthesiser.synthesise = AsyncMock(return_value=[])

        asyncio.get_event_loop().run_until_complete(
            synthesise_implications_node(ctx, self._make_config(synthesiser))
        )

        synthesiser.synthesise.assert_called_once()
