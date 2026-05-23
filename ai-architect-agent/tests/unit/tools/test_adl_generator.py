"""
Tests for ADLGeneratorV2Tool — Mark Richards ADL specification.

Covers _rejection_reason(), _validate_blocks(), run(), and
_render_adl_document() per the Richards spec requirements.
"""

from __future__ import annotations

import json
import logging
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.models.context import AdlBlock, AdlMetadata
from app.tools.adl_generator import (
    ADLGeneratorV2Tool,
    MIN_ADL_SOURCE_LENGTH,
)
from app.tools.base import ToolExecutionException


# ── Fixtures and helpers ─────────────────────────────────────

def _valid_adl_source() -> str:
    """Return a minimal valid ADL source block."""
    return (
        "DEFINE SYSTEM Payment Platform AS com.payments\n"
        "  DEFINE SERVICE Payment Service AS payment_service\n"
        "  DEFINE SERVICE Fraud Service AS fraud_service\n"
        "\n"
        "ASSERT(payment_service has NO DEPENDENCY ON fraud_service CLASSES)"
    )


def _valid_block_dict(
    adl_id: str = "ADL-001",
    source: str | None = None,
    requires: str = "ArchUnit Java library",
    description: str = "Payment isolation rule",
    prompt: str = "Write an ArchUnit test verifying payment isolation",
    characteristic: str = "modularity",
    enforcement: str = "hard",
) -> dict:
    """Build a valid raw block dict for testing."""
    return {
        "adl_id": adl_id,
        "metadata": {
            "requires": requires,
            "description": description,
            "prompt": prompt,
        },
        "adl_source": _valid_adl_source() if source is None else source,
        "characteristic_enforced": characteristic,
        "enforcement_level": enforcement,
    }


def _valid_llm_response(count: int = 2) -> str:
    """Return a JSON array of valid ADL blocks."""
    blocks = []
    for i in range(1, count + 1):
        blocks.append(_valid_block_dict(
            adl_id=f"ADL-{i:03d}",
            enforcement="hard" if i == 1 else "soft",
            characteristic=f"char-{i}",
        ))
    return json.dumps(blocks)


# ── _rejection_reason() tests ────────────────────────────────

class TestRejectionReason:
    """Tests for ADLGeneratorV2Tool._rejection_reason()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> ADLGeneratorV2Tool:
        """Instantiate tool with mocked LLM client."""
        return ADLGeneratorV2Tool(mock_llm)

    def test_returns_none_for_valid_block(self, tool):
        """A fully valid block passes without rejection."""
        raw = _valid_block_dict()

        result = tool._rejection_reason(raw)

        assert result is None

    def test_rejects_blank_adl_source(self, tool):
        """Blank adl_source is rejected."""
        raw = _valid_block_dict(source="")

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "too short" in result

    def test_rejects_adl_source_below_min_length(self, tool):
        """adl_source shorter than MIN_ADL_SOURCE_LENGTH is rejected."""
        raw = _valid_block_dict(source="DEFINE SYSTEM X AS y\nASSERT(z)")

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "too short" in result
        assert str(MIN_ADL_SOURCE_LENGTH) in result

    def test_rejects_forbidden_keyword_require(self, tool):
        """REQUIRE (without S) in adl_source triggers rejection."""
        source = (
            "DEFINE SYSTEM Test AS com.test\n"
            "  DEFINE SERVICE Svc AS svc\n"
            "REQUIRE some_condition\n"
            "ASSERT(svc has NO DEPENDENCY ON other CLASSES)"
        )
        raw = _valid_block_dict(source=source)

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "REQUIRE" in result
        assert "REQUIRES" in result

    def test_rejects_missing_define_system(self, tool):
        """adl_source without DEFINE SYSTEM is rejected."""
        source = (
            "DEFINE SERVICE Payment AS payment_service\n"
            "DEFINE SERVICE Fraud AS fraud_service\n"
            "ASSERT(payment_service has NO DEPENDENCY ON fraud_service CLASSES)"
        )
        raw = _valid_block_dict(source=source)

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "DEFINE SYSTEM" in result

    def test_rejects_no_assert_or_foreach(self, tool):
        """adl_source without ASSERT or FOREACH is rejected."""
        source = (
            "DEFINE SYSTEM Platform AS com.platform\n"
            "  DEFINE SERVICE Alpha AS alpha\n"
            "  DEFINE SERVICE Beta AS beta\n"
            "  DEFINE CONST MAX_CONN AS 100"
        )
        raw = _valid_block_dict(source=source)

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "ASSERT" in result
        assert "FOREACH" in result

    def test_rejects_blank_metadata_requires(self, tool):
        """Blank metadata.requires is rejected."""
        raw = _valid_block_dict(requires="")

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "requires" in result.lower()

    def test_rejects_blank_metadata_prompt(self, tool):
        """Blank metadata.prompt is rejected."""
        raw = _valid_block_dict(prompt="")

        result = tool._rejection_reason(raw)

        assert result is not None
        assert "prompt" in result.lower()


# ── _validate_blocks() tests ─────────────────────────────────

class TestValidateBlocks:
    """Tests for ADLGeneratorV2Tool._validate_blocks()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> ADLGeneratorV2Tool:
        """Instantiate tool with mocked LLM client."""
        return ADLGeneratorV2Tool(mock_llm)

    def test_returns_empty_list_when_all_fail(self, tool):
        """All-invalid input yields an empty validated list."""
        blocks = [
            _valid_block_dict(source=""),
            _valid_block_dict(prompt=""),
        ]

        result = tool._validate_blocks(blocks)

        assert result == []

    def test_returns_only_passing_blocks(self, tool):
        """Mixed valid and invalid blocks: only valid ones pass."""
        valid = _valid_block_dict(adl_id="ADL-001")
        invalid = _valid_block_dict(adl_id="ADL-002", source="")

        result = tool._validate_blocks([valid, invalid])

        assert len(result) == 1
        assert result[0].adl_id == "ADL-001"

    def test_logs_warning_for_rejected_blocks(self, tool, caplog):
        """Each rejected block produces a WARNING log."""
        blocks = [
            _valid_block_dict(adl_id="ADL-BAD1", source=""),
            _valid_block_dict(adl_id="ADL-BAD2", prompt=""),
        ]

        with caplog.at_level(logging.WARNING):
            tool._validate_blocks(blocks)

        assert "ADL-BAD1" in caplog.text
        assert "ADL-BAD2" in caplog.text
        assert caplog.text.count("rejected") == 2

    def test_validated_blocks_are_adlblock_instances(self, tool):
        """Validated output is a list of AdlBlock Pydantic models."""
        blocks = [_valid_block_dict()]

        result = tool._validate_blocks(blocks)

        assert len(result) == 1
        assert isinstance(result[0], AdlBlock)
        assert isinstance(result[0].metadata, AdlMetadata)


# ── run() tests ──────────────────────────────────────────────

class TestADLGeneratorV2Tool:
    """Tests for ADLGeneratorV2Tool.run()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> ADLGeneratorV2Tool:
        """Instantiate tool with mocked LLM client."""
        return ADLGeneratorV2Tool(mock_llm)

    @pytest.fixture
    def rich_context(self, base_context: ArchitectureContext) -> ArchitectureContext:
        """Context with architecture_design, trade_offs, and characteristics populated."""
        base_context.parsed_entities = {
            "domain": "fintech",
            "system_type": "payment platform",
        }
        base_context.architecture_design = {
            "style": "event-driven microservices",
            "components": [
                {"name": "PaymentGateway", "type": "service"},
                {"name": "FraudEngine", "type": "service"},
            ],
        }
        base_context.trade_offs = [
            {
                "decision_id": "TD-001",
                "decision": "Use async messaging",
                "optimises_characteristics": ["scalability"],
                "sacrifices_characteristics": ["consistency"],
            },
        ]
        base_context.characteristics = [
            {"name": "scalability"},
            {"name": "reliability"},
        ]
        return base_context

    async def test_raises_when_architecture_design_is_empty(
        self, tool, base_context,
    ):
        """run() raises ToolExecutionException when architecture_design is empty."""
        with pytest.raises(ToolExecutionException, match="architecture design"):
            await tool.run(base_context)

    async def test_warns_when_trade_offs_empty(
        self, tool, rich_context, mock_llm, caplog,
    ):
        """run() logs WARNING when trade_offs is empty, does not raise."""
        rich_context.trade_offs = []
        mock_llm.complete.return_value = _valid_llm_response()

        with caplog.at_level(logging.WARNING):
            result = await tool.run(rich_context)

        assert "trade-off decisions" in caplog.text
        assert len(result.adl_blocks) > 0

    async def test_calls_llm_with_json_format(
        self, tool, rich_context, mock_llm,
    ):
        """run() passes response_format='json' to llm_client.complete()."""
        mock_llm.complete.return_value = _valid_llm_response()

        await tool.run(rich_context)

        mock_llm.complete.assert_awaited_once()
        call_kwargs = mock_llm.complete.call_args
        assert call_kwargs.kwargs.get("response_format") == "json" or \
               (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "json")

    async def test_writes_adl_blocks_as_adlblock_instances(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes adl_blocks as a list of AdlBlock Pydantic models."""
        mock_llm.complete.return_value = _valid_llm_response()

        result = await tool.run(rich_context)

        assert len(result.adl_blocks) == 2
        assert all(isinstance(b, AdlBlock) for b in result.adl_blocks)

    async def test_writes_adl_rules_as_dicts_for_backward_compat(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes adl_rules as a list of dicts (backward compatibility)."""
        mock_llm.complete.return_value = _valid_llm_response()

        result = await tool.run(rich_context)

        assert len(result.adl_rules) == 2
        assert all(isinstance(r, dict) for r in result.adl_rules)
        # Each dict should have the adl_id field
        assert result.adl_rules[0]["adl_id"] == "ADL-001"

    async def test_writes_non_empty_adl_document(
        self, tool, rich_context, mock_llm,
    ):
        """run() writes a non-empty adl_document string to context."""
        mock_llm.complete.return_value = _valid_llm_response()

        result = await tool.run(rich_context)

        assert isinstance(result.adl_document, str)
        assert len(result.adl_document) > 0

    async def test_does_not_mutate_other_context_fields(
        self, tool, rich_context, mock_llm,
    ):
        """run() only writes adl_blocks, adl_rules, adl_document."""
        mock_llm.complete.return_value = _valid_llm_response()
        original_design = rich_context.architecture_design.copy()
        original_weaknesses = rich_context.weaknesses.copy()
        original_trade_offs = rich_context.trade_offs.copy()

        result = await tool.run(rich_context)

        assert result.architecture_design == original_design
        assert result.weaknesses == original_weaknesses
        assert result.trade_offs == original_trade_offs

    async def test_filters_blocks_that_fail_validation(
        self, tool, rich_context, mock_llm,
    ):
        """run() filters invalid blocks before writing to context."""
        blocks = [
            _valid_block_dict(adl_id="ADL-001"),
            _valid_block_dict(adl_id="ADL-002", source=""),
            _valid_block_dict(adl_id="ADL-003", prompt=""),
        ]
        mock_llm.complete.return_value = json.dumps(blocks)

        result = await tool.run(rich_context)

        assert len(result.adl_blocks) == 1
        assert result.adl_blocks[0].adl_id == "ADL-001"

    async def test_raises_on_invalid_json(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException when LLM returns invalid JSON."""
        mock_llm.complete.return_value = "{{not json at all"

        with pytest.raises(ToolExecutionException, match="invalid JSON"):
            await tool.run(rich_context)

    async def test_raises_on_non_array_json(
        self, tool, rich_context, mock_llm,
    ):
        """run() raises ToolExecutionException when LLM returns non-array JSON."""
        mock_llm.complete.return_value = json.dumps({"not": "an array"})

        with pytest.raises(ToolExecutionException, match="JSON array"):
            await tool.run(rich_context)


# ── _render_adl_document() tests ─────────────────────────────

class TestRenderAdlDocument:
    """Tests for ADLGeneratorV2Tool._render_adl_document()."""

    @pytest.fixture
    def tool(self, mock_llm: AsyncMock) -> ADLGeneratorV2Tool:
        """Instantiate tool with mocked LLM client."""
        return ADLGeneratorV2Tool(mock_llm)

    def _make_block(
        self,
        adl_id: str = "ADL-001",
        enforcement: str = "hard",
        requires: str = "ArchUnit Java library",
        description: str = "Test isolation",
        prompt: str = "Write ArchUnit test for isolation",
        source: str | None = None,
        characteristic: str = "modularity",
    ) -> AdlBlock:
        """Build an AdlBlock for render testing."""
        return AdlBlock(
            adl_id=adl_id,
            metadata=AdlMetadata(
                requires=requires,
                description=description,
                prompt=prompt,
            ),
            adl_source=source or _valid_adl_source(),
            characteristic_enforced=characteristic,
            enforcement_level=enforcement,
        )

    def test_includes_metadata_in_code_block(self, tool):
        """Rendered document includes REQUIRES, DESCRIPTION, PROMPT in adl fence."""
        block = self._make_block(
            requires="PyTestArch library",
            description="Service boundary check",
            prompt="Generate PyTestArch test",
        )

        doc = tool._render_adl_document([block])

        assert "REQUIRES PyTestArch library" in doc
        assert "DESCRIPTION Service boundary check" in doc
        assert "PROMPT Generate PyTestArch test" in doc

    def test_preserves_adl_source_verbatim(self, tool):
        """adl_source text appears verbatim inside a fenced code block."""
        source = _valid_adl_source()
        block = self._make_block(source=source)

        doc = tool._render_adl_document([block])

        # The source should appear as-is inside the document
        assert source in doc
        # It should be inside a fenced code block
        assert "```adl" in doc

    def test_groups_hard_and_soft_counts_in_header(self, tool):
        """Header line shows correct hard and soft enforcement counts."""
        blocks = [
            self._make_block(adl_id="ADL-001", enforcement="hard"),
            self._make_block(adl_id="ADL-002", enforcement="soft"),
            self._make_block(adl_id="ADL-003", enforcement="soft"),
        ]

        doc = tool._render_adl_document(blocks)

        assert "3 blocks total" in doc
        assert "1 hard enforcement" in doc
        assert "2 soft enforcement" in doc

    def test_produces_one_section_per_block(self, tool):
        """Each AdlBlock gets its own ## heading using adl_id."""
        blocks = [
            self._make_block(adl_id="ADL-001", description="First rule"),
            self._make_block(adl_id="ADL-002", description="Second rule"),
        ]

        doc = tool._render_adl_document(blocks)

        assert "## ADL-001: First rule" in doc
        assert "## ADL-002: Second rule" in doc
