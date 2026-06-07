"""Tests for app/tools/base.py — BaseTool abstract class and helpers."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from app.models import ArchitectureContext
from app.tools.base import BaseTool, ToolExecutionException


class _ConcreteToolA(BaseTool):
    """Concrete tool implementation for testing."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        return context


class _ConcreteToolWithSuffix(BaseTool):
    """Concrete tool that keeps the 'Tool' suffix in its class name."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        return context


class TestToolExecutionException:
    def test_is_exception_subclass(self):
        exc = ToolExecutionException("something went wrong")
        assert isinstance(exc, Exception)
        assert str(exc) == "something went wrong"


class TestBaseToolName:
    """Tests for BaseTool.name() which converts ClassName to snake_case."""

    def test_name_snake_cases_class_name(self, mock_llm):
        tool = _ConcreteToolA(mock_llm)
        # _ConcreteToolA -> _concrete_tool_a (lower)
        assert "concrete_tool_a" in tool.name()

    def test_name_removes_tool_suffix(self, mock_llm):
        # Class is _ConcreteToolWithSuffix; name() strips "Tool" via regex
        tool = _ConcreteToolWithSuffix(mock_llm)
        name = tool.name()
        assert isinstance(name, str)
        assert len(name) > 0


class TestBaseToolExecute:
    """Tests for BaseTool.execute() which sets LLM context then calls run()."""

    async def test_execute_calls_run(self, mock_llm):
        ctx = ArchitectureContext(
            raw_requirements="test", conversation_id="conv-42"
        )
        tool = _ConcreteToolA(mock_llm)

        with patch("app.tools.base.set_llm_context") as mock_set:
            result = await tool.execute(ctx)

        assert result is ctx
        mock_set.assert_called_once_with(tool.name(), "conv-42")

    async def test_execute_sets_correct_llm_context(self, mock_llm):
        ctx = ArchitectureContext(
            raw_requirements="test", conversation_id="my-conv"
        )
        tool = _ConcreteToolA(mock_llm)

        captured_args: list = []

        def _capture(*args):
            captured_args.extend(args)

        with patch("app.tools.base.set_llm_context", side_effect=_capture):
            await tool.execute(ctx)

        tool_name_arg, conv_id_arg = captured_args
        assert tool_name_arg == tool.name()
        assert conv_id_arg == "my-conv"
