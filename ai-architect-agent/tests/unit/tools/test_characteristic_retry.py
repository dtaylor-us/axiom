"""Tests for characteristic inference empty-output retry behavior."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.models import ArchitectureContext
from app.tools.base import ToolExecutionException
from app.tools.characteristic_reasoner import CharacteristicReasoningEngineTool


VALID_RETRY_RESPONSE = json.dumps({
    "characteristics": [
        {
            "name": "availability",
            "justification": "Payments need reliable authorization flow.",
            "measurable_target": "99.99% successful authorization availability.",
            "current_requirement_coverage": "implicit",
            "tensions_with": ["cost"],
        }
    ],
    "reasoning_summary": "Availability dominates the simplified scenario set.",
})


@pytest.fixture
def context_with_retry_inputs(base_context: ArchitectureContext) -> ArchitectureContext:
    """Return context with scenarios and parsed requirements for retry tests."""
    base_context.parsed_entities = {
        "domain": "fintech",
        "system_type": "payment platform",
        "functional_requirements": [{"id": f"F{i}"} for i in range(8)],
        "non_functional_requirements": [{"id": f"N{i}"} for i in range(4)],
    }
    base_context.scenarios = [{"id": f"S{i}"} for i in range(5)]
    return base_context


@pytest.mark.asyncio
async def test_characteristic_inference_retries_when_first_attempt_returns_empty(
    context_with_retry_inputs: ArchitectureContext,
) -> None:
    """Characteristic inference retries once when the first output is empty."""
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=["{}", VALID_RETRY_RESPONSE])

    with patch("app.tools.characteristic_reasoner.load_prompt", return_value="prompt"):
        result = await CharacteristicReasoningEngineTool(llm).run(
            context_with_retry_inputs
        )

    assert llm.complete.await_count == 2
    assert result.characteristics[0]["name"] == "availability"


@pytest.mark.asyncio
async def test_characteristic_inference_retries_with_top_three_scenarios_only(
    context_with_retry_inputs: ArchitectureContext,
) -> None:
    """The retry prompt receives only the first three budgeted scenarios."""
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=["{}", VALID_RETRY_RESPONSE])
    prompt_calls: list[dict] = []

    def capture_prompt(template_name: str, **kwargs: object) -> str:
        prompt_calls.append(kwargs)
        return "prompt"

    with patch(
        "app.tools.characteristic_reasoner.load_prompt",
        side_effect=capture_prompt,
    ):
        await CharacteristicReasoningEngineTool(llm).run(context_with_retry_inputs)

    assert prompt_calls[1]["scenarios"] == [{"id": "S0"}, {"id": "S1"}, {"id": "S2"}]


@pytest.mark.asyncio
async def test_characteristic_inference_raises_when_both_attempts_return_empty(
    context_with_retry_inputs: ArchitectureContext,
) -> None:
    """Characteristic inference raises when both attempts return empty output."""
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=["{}", "{}"])

    with patch("app.tools.characteristic_reasoner.load_prompt", return_value="prompt"):
        with pytest.raises(ToolExecutionException, match="both attempts"):
            await CharacteristicReasoningEngineTool(llm).run(context_with_retry_inputs)


@pytest.mark.asyncio
async def test_characteristic_inference_logs_warning_on_empty_first_attempt(
    context_with_retry_inputs: ArchitectureContext,
    caplog,
) -> None:
    """Characteristic inference logs a warning when the first output is empty."""
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=["{}", VALID_RETRY_RESPONSE])

    with patch("app.tools.characteristic_reasoner.load_prompt", return_value="prompt"):
        with caplog.at_level(logging.WARNING):
            await CharacteristicReasoningEngineTool(llm).run(
                context_with_retry_inputs
            )

    assert "returned empty characteristics" in caplog.text


@pytest.mark.asyncio
async def test_characteristic_inference_logs_success_on_retry(
    context_with_retry_inputs: ArchitectureContext,
    caplog,
) -> None:
    """Characteristic inference logs when the simplified retry succeeds."""
    llm = AsyncMock()
    llm.complete = AsyncMock(side_effect=["{}", VALID_RETRY_RESPONSE])

    with patch("app.tools.characteristic_reasoner.load_prompt", return_value="prompt"):
        with caplog.at_level(logging.INFO):
            await CharacteristicReasoningEngineTool(llm).run(
                context_with_retry_inputs
            )

    assert "retry succeeded" in caplog.text
