"""Tests for BaseTool.attempt_repair().

Covers ADL-035: single repair attempt per stage, repair prompt construction,
and propagation of LLMCallException as ToolExecutionException.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.client import LLMCallException
from app.tools.base import BaseTool, ToolExecutionException


class _ConcreteTestTool(BaseTool):
    """Minimal concrete subclass for testing BaseTool methods."""

    async def run(self, context):  # noqa: D102
        return context


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{"fixed": true}')
    return llm


@pytest.fixture
def tool(mock_llm):
    return _ConcreteTestTool(llm_client=mock_llm)


class TestAttemptRepair:
    """Tests for BaseTool.attempt_repair()."""

    async def test_repair_calls_llm_complete_once(self, tool, mock_llm):
        """attempt_repair() calls llm_client.complete() exactly once."""
        result = await tool.attempt_repair(
            original_prompt="Do the task.",
            failed_response='{"bad": json',
            error_description="Invalid JSON: ...",
        )
        mock_llm.complete.assert_awaited_once()
        assert result == '{"fixed": true}'

    async def test_repair_passes_output_schema_and_name(self, tool, mock_llm):
        """attempt_repair() forwards output_schema and schema_name to complete()."""
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        await tool.attempt_repair(
            original_prompt="Do the task.",
            failed_response="bad json",
            error_description="Invalid JSON",
            output_schema=schema,
            schema_name="my_stage",
        )
        _, kwargs = mock_llm.complete.call_args
        assert kwargs.get("output_schema") == schema
        assert kwargs.get("schema_name") == "my_stage"

    async def test_failed_response_truncated_to_500_chars(self, tool, mock_llm):
        """attempt_repair() truncates the failed_response to 500 chars in the repair prompt."""
        long_response = "x" * 1000
        await tool.attempt_repair(
            original_prompt="Do the task.",
            failed_response=long_response,
            error_description="Invalid JSON",
        )
        prompt_arg = mock_llm.complete.call_args[0][0]
        # The long response should appear truncated in the prompt
        assert "x" * 500 in prompt_arg
        assert "x" * 501 not in prompt_arg
        assert "[truncated...]" in prompt_arg

    async def test_repair_includes_error_description_in_prompt(self, tool, mock_llm):
        """attempt_repair() includes the error description in the repair prompt."""
        await tool.attempt_repair(
            original_prompt="Do the task.",
            failed_response="{}",
            error_description="JSONDecodeError: Expecting ',' at line 3",
        )
        prompt_arg = mock_llm.complete.call_args[0][0]
        assert "JSONDecodeError: Expecting ',' at line 3" in prompt_arg

    async def test_llm_call_exception_raises_tool_execution_exception(self, tool, mock_llm):
        """When llm_client.complete() raises LLMCallException, attempt_repair() raises ToolExecutionException."""
        mock_llm.complete.side_effect = LLMCallException("provider down")

        with pytest.raises(ToolExecutionException, match="provider down"):
            await tool.attempt_repair(
                original_prompt="Do the task.",
                failed_response="bad",
                error_description="Invalid JSON",
            )

    async def test_repair_logs_info(self, tool, mock_llm, caplog):
        """attempt_repair() logs at INFO level."""
        import logging
        with caplog.at_level(logging.INFO, logger="app.tools.base"):
            await tool.attempt_repair(
                original_prompt="Do the task.",
                failed_response="bad json",
                error_description="parse error",
            )
        assert any(
            "repair" in r.message.lower() or "repair" in r.msg.lower()
            for r in caplog.records
        )

    async def test_repair_prompt_includes_original_task(self, tool, mock_llm):
        """attempt_repair() includes the original prompt in the repair prompt."""
        await tool.attempt_repair(
            original_prompt="UNIQUE_ORIGINAL_TASK_STRING",
            failed_response="{}",
            error_description="error",
        )
        prompt_arg = mock_llm.complete.call_args[0][0]
        assert "UNIQUE_ORIGINAL_TASK_STRING" in prompt_arg
