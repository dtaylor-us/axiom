"""
Unit tests for proactive measure elicitation.

Tests verify that needs_measure scenarios surface in the generate_questions
prompt context and that the generate_response_node passes scenarios to the
prompt render call.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workshop.context import WorkshopContext, WorkshopScenario


def _ctx_with_scenarios(scenarios: list[WorkshopScenario]) -> WorkshopContext:
    return WorkshopContext(
        session_id="s-1",
        user_id="u-1",
        system_name="Payment Platform",
        scenarios=scenarios,
    )


def _scenario(sid: str, completeness: str) -> WorkshopScenario:
    measure = "p99 < 200ms" if completeness == "complete" else ""
    return WorkshopScenario(
        scenario_id=sid,
        title=f"Scenario {sid}",
        stimulus=f"a load spike {sid} occurs at peak trading hours",
        source="external user traffic",
        environment="peak trading hours in production",
        artifact="order processing service",
        response=f"serve requests {sid} without degradation or timeout",
        response_measure=measure,
        exercises_attributes=["performance"],
    )


class TestNeedsMeasureInPromptContext:
    def test_needs_measure_scenarios_appear_in_prompt_kwargs(self):
        """generate_response_node must pass workshop_scenarios to load_prompt."""
        needs_measure_scenario = _scenario("sc-1", "needs_measure")
        ctx = _ctx_with_scenarios([needs_measure_scenario, _scenario("sc-2", "complete")])

        captured_kwargs: dict = {}

        def fake_load_prompt(name: str, **kwargs):
            if name == "workshop/generate_questions":
                captured_kwargs.update(kwargs)
            return '{"agent_message": "ok", "clarifying_questions": [], "gap_progress": [], "workshop_scenarios": []}'

        with patch("app.workshop.nodes.load_prompt", side_effect=fake_load_prompt):
            from app.workshop.nodes import generate_response_node

            config = {
                "configurable": {
                    "llm_client": AsyncMock(complete=AsyncMock(
                        return_value=json.dumps({
                            "agent_message": "ok",
                            "clarifying_questions": [],
                            "gap_progress": [],
                            "workshop_scenarios": [],
                        })
                    )),
                    "consolidator": MagicMock(),
                    "reconciler": MagicMock(),
                    "resolver": MagicMock(),
                }
            }

            # Drive the node — ignore errors from missing consolidator logic,
            # we only care that load_prompt was called with workshop_scenarios.
            try:
                asyncio.run(generate_response_node(ctx, config))
            except Exception:
                pass  # ignore downstream errors

        assert "workshop_scenarios" in captured_kwargs, (
            "generate_response_node must pass workshop_scenarios to load_prompt"
        )

    def test_needs_measure_scenarios_not_filtered_from_kwargs(self):
        """All scenarios, including needs_measure, must appear in the prompt context."""
        sc1 = _scenario("sc-1", "needs_measure")
        sc2 = _scenario("sc-2", "partial")
        ctx = _ctx_with_scenarios([sc1, sc2])

        captured_scenarios: list = []

        def fake_load_prompt(name: str, **kwargs):
            if name == "workshop/generate_questions":
                captured_scenarios.extend(kwargs.get("workshop_scenarios", []))
            return json.dumps({"agent_message": "ok", "clarifying_questions": [], "gap_progress": [], "workshop_scenarios": []})

        with patch("app.workshop.nodes.load_prompt", side_effect=fake_load_prompt):
            from app.workshop.nodes import generate_response_node

            config = {
                "configurable": {
                    "llm_client": AsyncMock(complete=AsyncMock(
                        return_value=json.dumps({
                            "agent_message": "ok",
                            "clarifying_questions": [],
                            "gap_progress": [],
                            "workshop_scenarios": [],
                        })
                    )),
                    "consolidator": MagicMock(),
                    "reconciler": MagicMock(),
                    "resolver": MagicMock(),
                }
            }
            try:
                asyncio.run(generate_response_node(ctx, config))
            except Exception:
                pass

        assert len(captured_scenarios) == 2, (
            "All scenarios must be passed to the prompt — needs_measure must not be excluded"
        )

    def test_no_scenarios_produces_empty_list_in_prompt(self):
        """When no scenarios exist the prompt receives an empty list."""
        ctx = _ctx_with_scenarios([])
        captured_scenarios: list = []

        def fake_load_prompt(name: str, **kwargs):
            if name == "workshop/generate_questions":
                captured_scenarios.extend(kwargs.get("workshop_scenarios", []))
            return json.dumps({"agent_message": "ok", "clarifying_questions": [], "gap_progress": [], "workshop_scenarios": []})

        with patch("app.workshop.nodes.load_prompt", side_effect=fake_load_prompt):
            from app.workshop.nodes import generate_response_node

            config = {
                "configurable": {
                    "llm_client": AsyncMock(complete=AsyncMock(
                        return_value=json.dumps({
                            "agent_message": "ok",
                            "clarifying_questions": [],
                            "gap_progress": [],
                            "workshop_scenarios": [],
                        })
                    )),
                    "consolidator": MagicMock(),
                    "reconciler": MagicMock(),
                    "resolver": MagicMock(),
                }
            }
            try:
                asyncio.run(generate_response_node(ctx, config))
            except Exception:
                pass

        assert captured_scenarios == [], "Empty scenario list must propagate to prompt"
