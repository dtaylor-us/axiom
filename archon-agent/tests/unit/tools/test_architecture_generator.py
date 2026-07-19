"""Tests for ArchitectureGeneratorTool — style selection validation.

Covers the characteristic-driven style selection process that scores
all eight Richards architecture styles, applies veto rules, and
validates the selection rationale before producing a component design.
"""

from __future__ import annotations

import json
import logging
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.memory.store import MemoryStore
import app.tools.architecture_generator as architecture_generator_module
from app.tools.architecture_generator import (
    ArchitectureGeneratorTool,
    EXPECTED_STYLE_COUNT,
    MIN_RATIONALE_LENGTH,
)
from app.tools.base import ToolExecutionException


def _build_style_scores(
    selected: str = "Event-driven",
    runner_up: str = "Microservices",
    *,
    count: int = 8,
    vetoed_styles: dict[str, str] | None = None,
) -> list[dict]:
    """Build a style_scores list with the specified number of entries.

    Args:
        selected: Name to give the highest-scoring style.
        runner_up: Name to give the second-highest style.
        count: Total number of style entries to include.
        vetoed_styles: Mapping of style name to veto reason, if any.

    Returns:
        List of style score dicts in descending score order.
    """
    all_styles = [
        "Layered", "Modular Monolith", "Microkernel", "Pipeline",
        "Service-based", "Event-driven", "Microservices", "Space-based",
    ]
    vetoed_styles = vetoed_styles or {}
    scores = []
    for i, name in enumerate(all_styles[:count]):
        score_val = 20 - i * 2
        if name == selected:
            score_val = 25
        elif name == runner_up:
            score_val = 22
        entry: dict = {
            "style": name,
            "score": score_val,
            "driving_characteristics": ["scalability", "elasticity"],
            "vetoed": name in vetoed_styles,
            "veto_reason": vetoed_styles.get(name),
        }
        scores.append(entry)
    return scores


def _build_valid_response(
    selected_style: str = "Event-driven",
    runner_up: str = "Microservices",
    rationale: str | None = None,
    *,
    score_count: int = 8,
    include_reconsider: bool = True,
    vetoed_styles: dict[str, str] | None = None,
) -> str:
    """Build a valid JSON response string matching the updated schema.

    Args:
        selected_style: The style selection winner.
        runner_up: Second-place style.
        rationale: Override for the selection rationale text.
        score_count: Number of style_scores entries to include.
        include_reconsider: Whether to include when_to_reconsider_this_style.
        vetoed_styles: Dict mapping style name to veto reason.

    Returns:
        JSON string of a complete architecture generator response.
    """
    if rationale is None:
        rationale = (
            "Event-driven architecture scores highest because the primary "
            "characteristics — scalability, elasticity, and performance — "
            "all favour asynchronous decoupled processing. Microservices "
            "was the runner-up but was penalised by the small team size "
            "veto rule, making event-driven the pragmatic choice for this "
            "fraud detection system that must handle 5000 TPS with 10x "
            "peak elasticity."
        )
    result: dict = {
        "style_selection": {
            "override_applied": False,
            "override_type": "none",
            "override_warning": "",
            "candidate_scores": [],
            "style_scores": _build_style_scores(
                selected_style, runner_up,
                count=score_count,
                vetoed_styles=vetoed_styles,
            ),
            "selected_style": selected_style,
            "runner_up": runner_up,
            "selection_rationale": rationale,
            "is_hybrid": False,
            "hybrid_description": None,
        },
        "style": selected_style,
        "domain": "fintech",
        "system_type": "payment platform",
        "rationale": "Event-driven for high-throughput fraud detection.",
        "components": [
            {
                "name": "PaymentGateway",
                "type": "service",
                "responsibility": "Accepts incoming payment requests",
                "technology": "Java / Spring Boot",
                "technology_rationale": "Strong typing for financial domain",
                "characteristic_drivers": ["scalability", "performance"],
                "exposes": ["POST /payments"],
                "depends_on": ["FraudEngine"],
            },
            {
                "name": "FraudEngine",
                "type": "service",
                "responsibility": "Real-time fraud scoring",
                "technology": "Python / FastAPI",
                "technology_rationale": "ML model serving with low latency",
                "characteristic_drivers": ["performance", "scalability"],
                "exposes": ["fraud.scored event"],
                "depends_on": ["EventBus"],
            },
        ],
        "interactions": [
            {
                "from": "PaymentGateway",
                "to": "FraudEngine",
                "pattern": "async-event",
                "description": "Payment submitted for fraud check",
                "rationale": "Async to avoid blocking the payment flow",
            },
        ],
        "primary_flow": {
            "description": "Process a payment",
            "steps": [
                {"step": 1, "component": "PaymentGateway", "action": "Validate"},
                {"step": 2, "component": "FraudEngine", "action": "Score"},
            ],
        },
        "characteristic_coverage": {
            "well_addressed": ["scalability", "performance"],
            "partially_addressed": ["elasticity"],
            "deferred": ["observability"],
        },
    }
    if include_reconsider:
        result["when_to_reconsider_this_style"] = [
            "If TPS exceeds 50,000 sustained, migrate to space-based.",
            "If team grows beyond 15, consider microservices.",
        ]
    else:
        result["when_to_reconsider_this_style"] = []
    return json.dumps(result)


# Keep the old fixture string for backward-compatible tests
VALID_RESPONSE = _build_valid_response()


class TestArchitectureGeneratorTool:
    """Tests for ArchitectureGeneratorTool.run() — style selection validation."""

    @pytest.fixture
    def mock_memory(self) -> AsyncMock:
        """Return an AsyncMock of MemoryStore with empty similarity results."""
        memory = AsyncMock(spec=MemoryStore)
        memory.retrieve_similar = AsyncMock(return_value=[])
        return memory

    @pytest.fixture
    def tool(
        self, mock_llm: AsyncMock, mock_memory: AsyncMock
    ) -> ArchitectureGeneratorTool:
        """Return an ArchitectureGeneratorTool wired to mocked dependencies."""
        return ArchitectureGeneratorTool(mock_llm, mock_memory)

    @pytest.fixture
    def rich_context(
        self, base_context: ArchitectureContext
    ) -> ArchitectureContext:
        """Context with characteristics and conflicts already populated."""
        base_context.parsed_entities = {
            "domain": "fintech",
            "system_type": "payment platform",
        }
        base_context.characteristics = [
            {"name": "scalability", "tensions_with": ["cost-efficiency"]},
            {"name": "latency", "tensions_with": ["security"]},
        ]
        base_context.characteristic_conflicts = [
            {"characteristic_a": "latency", "characteristic_b": "security"},
        ]
        base_context.scenarios = [
            {"tier": "medium", "description": "5k TPS normal load"},
        ]
        return base_context

    # ------------------------------------------------------------------
    # Style selection validation tests
    # ------------------------------------------------------------------

    async def test_raises_when_style_selection_missing(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException when style_selection is absent."""
        response = json.loads(VALID_RESPONSE)
        del response["style_selection"]
        mock_llm.complete.return_value = json.dumps(response)

        with pytest.raises(
            ToolExecutionException,
            match="did not perform style selection",
        ):
            await tool.run(rich_context)

    async def test_raises_when_selected_style_blank(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException when selected_style is blank."""
        mock_llm.complete.return_value = _build_valid_response(
            selected_style="",
        )

        with pytest.raises(
            ToolExecutionException,
            match="blank style selection",
        ):
            await tool.run(rich_context)

    async def test_warns_when_fewer_than_eight_style_scores(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when style_scores has fewer than 8 entries."""
        mock_llm.complete.return_value = _build_valid_response(
            score_count=5,
        )

        with caplog.at_level(logging.WARNING):
            await tool.run(rich_context)

        assert any(
            "scored only 5" in record.message
            for record in caplog.records
        )

    async def test_warns_when_rationale_too_short(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when rationale is fewer than 100 characters."""
        mock_llm.complete.return_value = _build_valid_response(
            rationale="Too short.",
        )

        with caplog.at_level(logging.WARNING):
            await tool.run(rich_context)

        assert any(
            "rationale is too brief" in record.message
            for record in caplog.records
        )

    async def test_warns_when_layered_selected_with_scalability(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when Layered is selected despite scalability."""
        mock_llm.complete.return_value = _build_valid_response(
            selected_style="Layered",
            runner_up="Service-based",
        )

        with caplog.at_level(logging.WARNING):
            await tool.run(rich_context)

        assert any(
            "Layered architecture selected despite quality" in record.message
            for record in caplog.records
        )

    async def test_warns_when_reconsider_list_empty(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when when_to_reconsider_this_style is empty."""
        mock_llm.complete.return_value = _build_valid_response(
            include_reconsider=False,
        )

        with caplog.at_level(logging.WARNING):
            await tool.run(rich_context)

        assert any(
            "no when_to_reconsider_this_style" in record.message
            for record in caplog.records
        )

    async def test_writes_style_selection_into_architecture_design(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes style_selection into architecture_design."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert "style_selection" in result.architecture_design
        assert (
            result.architecture_design["style_selection"]["selected_style"]
            == "Event-driven"
        )

    async def test_run_writes_override_applied_to_architecture_design(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes override_applied into architecture_design root for payload."""
        response = json.loads(VALID_RESPONSE)
        response["style_selection"]["override_applied"] = True
        response["style_selection"]["override_type"] = "pinned"
        response["style_selection"]["override_warning"] = ""
        mock_llm.complete.return_value = json.dumps(response)

        result = await tool.run(rich_context)

        assert result.architecture_design["override_applied"] is True

    async def test_run_writes_override_warning_to_architecture_design(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes override_warning into architecture_design root for payload."""
        response = json.loads(VALID_RESPONSE)
        response["style_selection"]["override_applied"] = True
        response["style_selection"]["override_type"] = "pinned"
        response["style_selection"]["override_warning"] = "Poor fit warning."
        mock_llm.complete.return_value = json.dumps(response)

        result = await tool.run(rich_context)

        assert result.architecture_design["override_warning"] == "Poor fit warning."

    async def test_run_logs_warning_when_override_warning_non_empty(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when override_warning is non-empty."""
        response = json.loads(VALID_RESPONSE)
        response["style_selection"]["override_applied"] = True
        response["style_selection"]["override_type"] = "pinned"
        response["style_selection"]["override_warning"] = "Poor fit warning."
        mock_llm.complete.return_value = json.dumps(response)

        with caplog.at_level(logging.WARNING):
            await tool.run(rich_context)

        assert any(
            "override produced a poor-fit selection" in r.message
            for r in caplog.records
        )

    async def test_run_passes_architecture_override_to_prompt_loader(
        self, tool, rich_context, mock_llm, monkeypatch,
    ):
        """run() passes architecture_override to the prompt loader call."""
        mock_llm.complete.return_value = VALID_RESPONSE
        rich_context.architecture_override = {
            "type": "pinned",
            "styles": ["event-driven"],
            "raw_instruction": "Use event-driven",
            "detected_confidence": "high",
        }
        rich_context.buy_vs_build_preferences = {"build_preference": "neutral"}

        captured: dict = {}

        def _fake_load_prompt(name: str, **kwargs):
            captured["name"] = name
            captured["kwargs"] = kwargs
            return "prompt"

        monkeypatch.setattr(architecture_generator_module, "load_prompt", _fake_load_prompt)

        await tool.run(rich_context)

        assert captured["name"] == "architecture_generator"
        assert "architecture_override" in captured["kwargs"]
        assert captured["kwargs"]["architecture_override"]["type"] == "pinned"
        assert "buy_vs_build_preferences" in captured["kwargs"]

    async def test_writes_style_scores_to_context_field(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes architecture_style_scores to the dedicated field."""
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert len(result.architecture_style_scores) == EXPECTED_STYLE_COUNT

    async def test_selected_style_overwrites_conflicting_legacy_style(
        self, tool, rich_context, mock_llm,
    ):
        """Chat formatting and persistence receive one canonical style."""
        response = json.loads(VALID_RESPONSE)
        response["style"] = "Modular Monolith"
        mock_llm.complete.return_value = json.dumps(response)

        result = await tool.run(rich_context)

        assert result.selected_architecture_style == "Event-driven"
        assert result.architecture_design["style"] == "Event-driven"

    async def test_does_not_raise_when_all_eight_scored(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() succeeds without warnings when all 8 styles scored properly."""
        mock_llm.complete.return_value = VALID_RESPONSE

        with caplog.at_level(logging.WARNING):
            result = await tool.run(rich_context)

        # No scored-only warning should fire for full 8
        scored_warnings = [
            r for r in caplog.records if "scored only" in r.message
        ]
        assert not scored_warnings
        assert result.architecture_design["style"] == "Event-driven"

    # ------------------------------------------------------------------
    # Existing tests (preserved from original file)
    # ------------------------------------------------------------------

    async def test_raises_when_characteristics_empty(
        self, tool, mock_llm,
    ):
        """run() raises ToolExecutionException when characteristics is empty."""
        ctx = ArchitectureContext(raw_requirements="test")

        with pytest.raises(
            ToolExecutionException, match="characteristics is empty"
        ):
            await tool.run(ctx)

    async def test_calls_memory_retrieve(
        self, tool, rich_context, mock_llm, mock_memory,
    ):
        """run() retrieves similar designs from memory store."""
        mock_llm.complete.return_value = VALID_RESPONSE

        await tool.run(rich_context)

        mock_memory.retrieve_similar.assert_awaited_once_with(
            rich_context.raw_requirements, limit=3
        )

    async def test_raises_when_components_list_empty(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException when components list is empty."""
        response = json.loads(VALID_RESPONSE)
        response["components"] = []
        mock_llm.complete.return_value = json.dumps(response)

        with pytest.raises(
            ToolExecutionException, match="empty components list"
        ):
            await tool.run(rich_context)

    async def test_raises_on_invalid_json(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException on invalid JSON."""
        mock_llm.complete.return_value = "broken json"

        with pytest.raises(
            ToolExecutionException, match="repair attempt"
        ):
            await tool.run(rich_context)

    async def test_stores_similar_past_designs(
        self, tool, rich_context, mock_llm, mock_memory,
    ):
        """run() stores retrieved similar designs in context."""
        mock_memory.retrieve_similar.return_value = [
            {"conversation_id": "past-1", "domain": "fintech"},
        ]
        mock_llm.complete.return_value = VALID_RESPONSE

        result = await tool.run(rich_context)

        assert len(result.similar_past_designs) == 1
        assert result.similar_past_designs[0]["domain"] == "fintech"


class TestArchitectureContextStyleProperty:
    """Tests for ArchitectureContext.selected_architecture_style property."""

    def test_returns_style_when_populated(self):
        """selected_architecture_style returns the style name from design."""
        ctx = ArchitectureContext(
            architecture_design={
                "style_selection": {"selected_style": "Service-based"},
            }
        )

        assert ctx.selected_architecture_style == "Service-based"

    def test_returns_empty_when_design_empty(self):
        """selected_architecture_style returns empty string when no design."""
        ctx = ArchitectureContext()

        assert ctx.selected_architecture_style == ""

    def test_returns_empty_when_style_selection_missing(self):
        """selected_architecture_style returns empty when style_selection absent."""
        ctx = ArchitectureContext(
            architecture_design={"style": "Layered"}
        )

        assert ctx.selected_architecture_style == ""
