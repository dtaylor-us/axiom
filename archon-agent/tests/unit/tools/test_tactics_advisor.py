"""Unit tests for TacticsAdvisorTool.

Verifies:
- run() guards (characteristics required; architecture_design optional)
- LLM call parameters
- Context field writes (tactics, tactics_summary)
- Per-tactic validation + filtering
- Warning/info logging
- No mutation of unrelated context fields

Tactic catalog source:
    Bass, Clements, Kazman "Software Architecture in Practice"
    4th ed., SEI/Addison-Wesley 2021.
"""

from __future__ import annotations

import json
import logging
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.tools.tactics_advisor import (
    TacticsAdvisorTool,
    MIN_TACTICS,
    MIN_DESCRIPTION_LENGTH,
    MIN_CONCRETE_APPLICATION_LENGTH,
    VALID_EFFORT,
    VALID_PRIORITY,
)
from app.tools.base import ToolExecutionException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_tactic(**overrides) -> dict:
    """Return a minimal valid raw tactic dict, optionally overriding fields."""
    base = {
        "tactic_id": "T-001",
        "tactic_name": "Circuit Breaker",
        "characteristic_name": "availability",
        "category": "detect faults",
        "description": "Prevent cascading failures by tripping when downstream calls fail repeatedly.",
        "concrete_application": (
            "Wrap the payment gateway HTTP client in a Resilience4j circuit breaker "
            "with a 50% failure ratio threshold and 10-second wait-duration-in-open-state."
        ),
        "implementation_examples": ["Resilience4j CircuitBreaker", "Hystrix"],
        "already_addressed": False,
        "address_evidence": "",
        "effort": "medium",
        "priority": "critical",
    }
    base.update(overrides)
    return base


def _llm_resp(tactics: list[dict], summary: str = "Default tactic summary.") -> str:
    return json.dumps({"tactics": tactics, "tactics_summary": summary})


def _min_valid_set(count: int = MIN_TACTICS) -> list[dict]:
    """Return *count* distinct valid tactics so the min-count guard is satisfied."""
    characteristics = ["availability", "performance", "security", "modifiability", "testability"]
    tactics = []
    for i in range(count):
        char = characteristics[i % len(characteristics)]
        tactics.append(_make_valid_tactic(tactic_id=f"T-{i:03d}", characteristic_name=char))
    return tactics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tool(mock_llm: AsyncMock) -> TacticsAdvisorTool:
    return TacticsAdvisorTool(mock_llm)


@pytest.fixture
def context_with_chars(base_context: ArchitectureContext) -> ArchitectureContext:
    """Context with characteristics populated (stage 4 complete)."""
    base_context.parsed_entities = {"domain": "fintech", "system_type": "payment platform"}
    base_context.characteristics = [
        {"name": "availability", "tensions_with": ["cost-efficiency"]},
        {"name": "performance", "tensions_with": ["security"]},
    ]
    return base_context


@pytest.fixture
def context_with_design(context_with_chars: ArchitectureContext) -> ArchitectureContext:
    """Context with both characteristics and architecture_design populated."""
    context_with_chars.architecture_design = (
        "Microservices on Kubernetes with an API gateway and service mesh."
    )
    return context_with_chars


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

class TestRunGuards:
    """run() guard behaviour."""

    async def test_raises_when_characteristics_empty(self, tool: TacticsAdvisorTool):
        """run() raises ToolExecutionException when characteristics is empty."""
        ctx = ArchitectureContext(raw_requirements="test")

        with pytest.raises(ToolExecutionException, match="characteristics"):
            await tool.run(ctx)

    async def test_warns_when_architecture_design_empty(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() logs WARNING when architecture_design is empty but does not raise."""
        mock_llm.complete.return_value = _llm_resp(_min_valid_set())

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert result is context_with_chars
        assert any(
            "architecture design" in rec.message.lower()
            or "concrete_application" in rec.message.lower()
            for rec in caplog.records
        )

    async def test_does_not_raise_when_architecture_design_empty(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() continues normally when architecture_design is empty."""
        mock_llm.complete.return_value = _llm_resp(_min_valid_set())
        # Should not raise
        result = await tool.run(context_with_chars)
        assert isinstance(result.tactics, list)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

class TestLlmCall:
    """run() LLM client interaction."""

    async def test_calls_llm_complete_with_json_response_format(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() calls llm_client.complete with response_format='json'."""
        mock_llm.complete.return_value = _llm_resp(_min_valid_set())

        await tool.run(context_with_chars)

        mock_llm.complete.assert_awaited_once()
        _, kwargs = mock_llm.complete.call_args
        assert kwargs.get("response_format") == "json"

    async def test_raises_on_invalid_json(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() raises ToolExecutionException when LLM returns invalid JSON."""
        mock_llm.complete.return_value = "this is not json at all"

        with pytest.raises(ToolExecutionException, match="repair attempt"):
            await tool.run(context_with_chars)


# ---------------------------------------------------------------------------
# Context writes
# ---------------------------------------------------------------------------

class TestContextWrites:
    """run() writes the correct fields to the context."""

    async def test_writes_tactics_list_to_context(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() writes tactics list to context.tactics as a list of dicts."""
        tactics = _min_valid_set()
        mock_llm.complete.return_value = _llm_resp(tactics)

        result = await tool.run(context_with_chars)

        assert isinstance(result.tactics, list)
        assert len(result.tactics) == len(tactics)
        assert all(isinstance(t, dict) for t in result.tactics)

    async def test_writes_tactics_summary_string(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() writes the tactics_summary string from LLM output."""
        expected_summary = "Availability and performance are the dominant quality concerns."
        mock_llm.complete.return_value = _llm_resp(_min_valid_set(), summary=expected_summary)

        result = await tool.run(context_with_chars)

        assert result.tactics_summary == expected_summary

    async def test_does_not_mutate_other_context_fields(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() does not mutate other ArchitectureContext fields."""
        original_chars = context_with_chars.characteristics.copy()
        original_entities = dict(context_with_chars.parsed_entities)
        mock_llm.complete.return_value = _llm_resp(_min_valid_set())

        await tool.run(context_with_chars)

        assert context_with_chars.characteristics == original_chars
        assert context_with_chars.parsed_entities == original_entities


# ---------------------------------------------------------------------------
# Per-tactic filtering
# ---------------------------------------------------------------------------

class TestTacticFiltering:
    """run() filters invalid tactics before writing to context."""

    async def _run_with_one_tactic(self, tool, context, mock_llm, tactic: dict) -> list[dict]:
        """Helper: run with exactly one tactic in the response (below MIN_TACTICS)."""
        mock_llm.complete.return_value = _llm_resp([tactic])
        result = await tool.run(context)
        return result.tactics

    async def test_accepts_valid_tactic(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
    ):
        """run() keeps a fully valid tactic in the output."""
        valid = _make_valid_tactic()
        mock_llm.complete.return_value = _llm_resp([valid] + _min_valid_set())

        result = await tool.run(context_with_chars)

        assert any(t["tactic_name"] == "Circuit Breaker" for t in result.tactics)

    async def test_filters_tactic_with_blank_tactic_name(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with blank tactic_name."""
        bad = _make_valid_tactic(tactic_id="BAD-001", tactic_name="")
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_filters_tactic_with_short_description(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with description shorter than MIN_DESCRIPTION_LENGTH."""
        short_desc = "Too short"
        assert len(short_desc) < MIN_DESCRIPTION_LENGTH
        bad = _make_valid_tactic(tactic_id="BAD-002", description=short_desc)
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_filters_tactic_with_short_concrete_application(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with concrete_application shorter than MIN_CONCRETE_APPLICATION_LENGTH."""
        short_app = "Use caching."
        assert len(short_app) < MIN_CONCRETE_APPLICATION_LENGTH
        bad = _make_valid_tactic(tactic_id="BAD-003", concrete_application=short_app)
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_filters_tactic_with_invalid_effort(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with invalid effort value."""
        bad = _make_valid_tactic(tactic_id="BAD-004", effort="extreme")
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_filters_tactic_with_invalid_priority(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with invalid priority value."""
        bad = _make_valid_tactic(tactic_id="BAD-005", priority="urgent")
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_filters_tactic_with_empty_implementation_examples(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() filters tactics with empty implementation_examples list."""
        bad = _make_valid_tactic(tactic_id="BAD-006", implementation_examples=[])
        mock_llm.complete.return_value = _llm_resp([bad])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            result = await tool.run(context_with_chars)

        assert len(result.tactics) == 0

    async def test_logs_warning_for_each_filtered_tactic(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() logs a WARNING for each rejected tactic."""
        bad1 = _make_valid_tactic(tactic_id="BAD-A", tactic_name="")
        bad2 = _make_valid_tactic(tactic_id="BAD-B", effort="oops")
        mock_llm.complete.return_value = _llm_resp([bad1, bad2])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            await tool.run(context_with_chars)

        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        # At least one warning per rejected tactic (two rejects + possibly the
        # low-count warning)
        assert len(warning_messages) >= 2
        assert any("BAD-A" in m or "BAD-B" in m for m in warning_messages)


# ---------------------------------------------------------------------------
# Minimum tactics count warning
# ---------------------------------------------------------------------------

class TestMinimumTacticsWarning:
    """run() warns when fewer than MIN_TACTICS pass validation."""

    async def test_logs_warning_when_fewer_than_min_tactics(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() logs WARNING when fewer than MIN_TACTICS pass validation."""
        assert MIN_TACTICS > 1, "test assumption: MIN_TACTICS > 1"
        # Provide only 1 valid tactic (below MIN_TACTICS)
        mock_llm.complete.return_value = _llm_resp([_make_valid_tactic()])

        with caplog.at_level(logging.WARNING, logger="app.tools.tactics_advisor"):
            await tool.run(context_with_chars)

        assert any(
            str(MIN_TACTICS) in rec.message or "minimum" in rec.message.lower()
            for rec in caplog.records
            if rec.levelno == logging.WARNING
        )


# ---------------------------------------------------------------------------
# INFO logging
# ---------------------------------------------------------------------------

class TestInfoLogging:
    """run() logs INFO with already_addressed and new counts."""

    async def test_logs_info_with_already_addressed_count_and_new_count(
        self,
        tool: TacticsAdvisorTool,
        context_with_chars: ArchitectureContext,
        mock_llm: AsyncMock,
        caplog,
    ):
        """run() logs INFO with already_addressed count and new count."""
        addressed = _make_valid_tactic(tactic_id="A-001", already_addressed=True)
        new1 = _make_valid_tactic(tactic_id="A-002", characteristic_name="performance")
        new2 = _make_valid_tactic(tactic_id="A-003", characteristic_name="security")
        new3 = _make_valid_tactic(tactic_id="A-004", characteristic_name="modifiability")
        mock_llm.complete.return_value = _llm_resp([addressed, new1, new2, new3])

        with caplog.at_level(logging.INFO, logger="app.tools.tactics_advisor"):
            await tool.run(context_with_chars)

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        combined = " ".join(info_messages)
        assert "already_addressed" in combined or "already" in combined


# ---------------------------------------------------------------------------
# _validate_tactic
# ---------------------------------------------------------------------------

class TestValidateTactic:
    """_validate_tactic() unit tests — independent of run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> TacticsAdvisorTool:
        return TacticsAdvisorTool(mock_llm)

    def test_returns_none_for_fully_valid_tactic(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns None for a fully valid tactic dict."""
        result = tool._validate_tactic(_make_valid_tactic())
        assert result is None

    def test_returns_reason_when_tactic_name_blank(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when tactic_name is blank."""
        result = tool._validate_tactic(_make_valid_tactic(tactic_name=""))
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_reason_when_tactic_name_whitespace(self, tool: TacticsAdvisorTool):
        """_validate_tactic() rejects whitespace-only tactic_name."""
        result = tool._validate_tactic(_make_valid_tactic(tactic_name="   "))
        assert result is not None

    def test_returns_reason_when_description_too_short(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when description is too short."""
        short = "x" * (MIN_DESCRIPTION_LENGTH - 1)
        result = tool._validate_tactic(_make_valid_tactic(description=short))
        assert result is not None

    def test_accepts_description_at_exact_min_length(self, tool: TacticsAdvisorTool):
        """_validate_tactic() accepts description exactly at MIN_DESCRIPTION_LENGTH."""
        exact = "x" * MIN_DESCRIPTION_LENGTH
        result = tool._validate_tactic(_make_valid_tactic(description=exact))
        assert result is None

    def test_returns_reason_when_concrete_application_too_short(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when concrete_application is too short."""
        short = "x" * (MIN_CONCRETE_APPLICATION_LENGTH - 1)
        result = tool._validate_tactic(_make_valid_tactic(concrete_application=short))
        assert result is not None

    def test_accepts_concrete_application_at_exact_min_length(self, tool: TacticsAdvisorTool):
        """_validate_tactic() accepts concrete_application exactly at MIN_CONCRETE_APPLICATION_LENGTH."""
        exact = "x" * MIN_CONCRETE_APPLICATION_LENGTH
        result = tool._validate_tactic(_make_valid_tactic(concrete_application=exact))
        assert result is None

    def test_returns_reason_when_effort_invalid(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when effort is invalid value."""
        result = tool._validate_tactic(_make_valid_tactic(effort="extreme"))
        assert result is not None
        assert "effort" in result.lower() or "extreme" in result

    def test_accepts_all_valid_effort_values(self, tool: TacticsAdvisorTool):
        """_validate_tactic() accepts each valid effort value."""
        for effort in VALID_EFFORT:
            result = tool._validate_tactic(_make_valid_tactic(effort=effort))
            assert result is None, f"Expected None for effort='{effort}', got: {result}"

    def test_returns_reason_when_priority_invalid(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when priority is invalid value."""
        result = tool._validate_tactic(_make_valid_tactic(priority="urgent"))
        assert result is not None
        assert "priority" in result.lower() or "urgent" in result

    def test_accepts_all_valid_priority_values(self, tool: TacticsAdvisorTool):
        """_validate_tactic() accepts each valid priority value."""
        for priority in VALID_PRIORITY:
            result = tool._validate_tactic(_make_valid_tactic(priority=priority))
            assert result is None, f"Expected None for priority='{priority}', got: {result}"

    def test_returns_reason_when_implementation_examples_empty_list(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when implementation_examples is empty list."""
        result = tool._validate_tactic(_make_valid_tactic(implementation_examples=[]))
        assert result is not None

    def test_returns_reason_when_implementation_examples_not_list(self, tool: TacticsAdvisorTool):
        """_validate_tactic() returns reason when implementation_examples is not a list."""
        result = tool._validate_tactic(_make_valid_tactic(implementation_examples="not-a-list"))
        assert result is not None

    def test_returns_reason_string_not_empty(self, tool: TacticsAdvisorTool):
        """_validate_tactic() rejection reasons are non-empty strings."""
        cases = [
            _make_valid_tactic(tactic_name=""),
            _make_valid_tactic(description="short"),
            _make_valid_tactic(concrete_application="too short"),
            _make_valid_tactic(effort="bad"),
            _make_valid_tactic(priority="bad"),
            _make_valid_tactic(implementation_examples=[]),
        ]
        for case in cases:
            result = tool._validate_tactic(case)
            assert result is not None and len(result) > 0, (
                f"Expected non-empty reason for tactic: {case}"
            )
