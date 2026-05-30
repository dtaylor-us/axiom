"""Tests for elicit_scenarios_node evidence wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workshop.context import WorkshopContext
from app.workshop.nodes import elicit_scenarios_node


@pytest.mark.asyncio
async def test_elicit_scenarios_passes_all_evidence_and_existing_ids() -> None:
    captured: dict = {}

    def capture_prompt(_name: str, **kwargs: object) -> str:
        captured.update(kwargs)
        return "prompt"

    state = WorkshopContext(
        session_id="s",
        user_id="u",
        workshop_phase="risk_priority",
        current_turn=1,
        raw_inputs=["turn one story", "turn two detail"],
    )
    config = {
        "configurable": {
            "llm_client": MagicMock(complete=AsyncMock(return_value='{"scenarios": []}')),
            "latest_input": "latest",
        },
    }

    with patch("app.workshop.nodes.load_prompt", side_effect=capture_prompt):
        await elicit_scenarios_node(state, config)

    ev = captured.get("all_evidence")
    assert isinstance(ev, list) and len(ev) == 2
    assert captured.get("existing_scenario_ids") == []
    assert captured.get("latest_input") == "latest"
