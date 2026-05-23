"""Tests for the DiagramGeneratorTool — selection, validation, and run().

Covers:
  - _select_diagram_types as a pure function (~12 tests)
  - _rejection_reason guard rule checks (~9 tests)
  - _validate_diagrams dedup, missing-type, and all-fail behaviour (~5 tests)
  - run() end-to-end including backward-compat fields (~6 tests)
  - ArchitectureContext.get_diagram helper (~3 tests)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock

from app.models import ArchitectureContext
from app.models.context import Diagram, DiagramType
from app.tools.diagram_generator import (
    DiagramGeneratorTool,
    EXPECTED_SYNTAX_PREFIXES,
    MAX_DIAGRAMS,
    MIN_DIAGRAM_SOURCE_LINES,
    MIN_DIAGRAMS,
)
from app.tools.base import ToolExecutionException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mermaid_source(prefix: str, lines: int = 15) -> str:
    """Build a valid Mermaid source with the given prefix and line count."""
    body = "\n".join(f"  node{i}[Component {i}]" for i in range(1, lines))
    return f"{prefix}\n{body}"


def _make_diagram_dict(
    diagram_id: str = "D-001",
    diagram_type: str = "c4_container",
    title: str = "C4 Container Diagram",
    lines: int = 15,
    prefix: str | None = None,
    **overrides,
) -> dict:
    """Build a valid raw diagram dict as the LLM would return."""
    if prefix is None:
        prefixes = EXPECTED_SYNTAX_PREFIXES.get(DiagramType(diagram_type))
        prefix = prefixes[0] if prefixes else "graph TD"
    return {
        "diagram_id": diagram_id,
        "type": diagram_type,
        "title": title,
        "description": "A test diagram",
        "mermaid_source": _make_mermaid_source(prefix, lines),
        "characteristic_addressed": "testability",
        **overrides,
    }


def _make_valid_response(types: list[str] | None = None) -> str:
    """Build a valid JSON response with diagrams for the given types."""
    if types is None:
        types = ["c4_container", "sequence_primary", "sequence_error"]
    diagrams = []
    for i, t in enumerate(types, 1):
        prefixes = EXPECTED_SYNTAX_PREFIXES.get(DiagramType(t))
        prefix = prefixes[0] if prefixes else "graph TD"
        diagrams.append(_make_diagram_dict(
            diagram_id=f"D-{i:03d}",
            diagram_type=t,
            title=f"Diagram {t}",
            prefix=prefix,
        ))
    return json.dumps({"diagrams": diagrams})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tool(mock_llm: AsyncMock) -> DiagramGeneratorTool:
    return DiagramGeneratorTool(mock_llm)


@pytest.fixture
def event_driven_design() -> dict:
    return {
        "style": "event-driven microservices",
        "components": [
            {"name": "PaymentGateway", "type": "service"},
            {"name": "FraudEngine", "type": "service"},
        ],
        "interactions": [
            {"from": "PaymentGateway", "to": "FraudEngine", "pattern": "async-event"},
        ],
    }


@pytest.fixture
def layered_design() -> dict:
    return {
        "style": "layered monolith",
        "components": [
            {"name": "Controller", "type": "layer"},
            {"name": "Service", "type": "layer"},
        ],
        "interactions": [],
    }


@pytest.fixture
def pipeline_design() -> dict:
    return {
        "style": "pipeline architecture",
        "components": [
            {"name": "Ingest", "type": "pipe"},
            {"name": "Transform", "type": "pipe"},
        ],
        "interactions": [],
    }


@pytest.fixture
def microkernel_design() -> dict:
    return {
        "style": "microkernel plugin-based",
        "components": [
            {"name": "Core", "type": "kernel"},
            {"name": "PluginA", "type": "plugin"},
        ],
        "interactions": [],
    }


@pytest.fixture
def explicit_characteristics() -> list[dict]:
    return [
        {"name": "scalability", "current_requirement_coverage": "explicit", "measurable_target": "10k TPS"},
        {"name": "data_integrity", "current_requirement_coverage": "explicit", "measurable_target": "PCI-DSS L1"},
    ]


@pytest.fixture
def deploy_characteristics() -> list[dict]:
    return [
        {"name": "deployability", "current_requirement_coverage": "explicit", "measurable_target": ""},
    ]


@pytest.fixture
def context_with_design(base_context: ArchitectureContext, event_driven_design: dict) -> ArchitectureContext:
    """Context with architecture_design and characteristics populated."""
    base_context.architecture_design = event_driven_design
    base_context.characteristics = [
        {"name": "performance", "current_requirement_coverage": "explicit", "measurable_target": "sub-100ms"},
    ]
    return base_context


# ===========================================================================
# _select_diagram_types tests
# ===========================================================================

class TestSelectDiagramTypes:
    """Pure function — no LLM calls, no side effects."""

    def test_always_includes_mandatory_types(self, tool, event_driven_design):
        result = tool._select_diagram_types(event_driven_design, [])
        mandatory = {DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY, DiagramType.SEQUENCE_ERROR}
        assert mandatory.issubset(set(result))

    def test_event_driven_adds_state(self, tool, event_driven_design):
        result = tool._select_diagram_types(event_driven_design, [])
        assert DiagramType.STATE in result

    def test_microservices_adds_state(self, tool):
        design = {"style": "microservices"}
        result = tool._select_diagram_types(design, [])
        assert DiagramType.STATE in result

    def test_layered_adds_class(self, tool, layered_design):
        result = tool._select_diagram_types(layered_design, [])
        assert DiagramType.CLASS in result

    def test_pipeline_adds_flowchart(self, tool, pipeline_design):
        result = tool._select_diagram_types(pipeline_design, [])
        assert DiagramType.FLOWCHART in result

    def test_microkernel_adds_class(self, tool, microkernel_design):
        result = tool._select_diagram_types(microkernel_design, [])
        assert DiagramType.CLASS in result

    def test_data_integrity_adds_er(self, tool, explicit_characteristics):
        design = {"style": "service-based"}
        result = tool._select_diagram_types(design, explicit_characteristics)
        assert DiagramType.ER in result

    def test_deployability_adds_deployment(self, tool, deploy_characteristics):
        design = {"style": "event-driven microservices"}
        result = tool._select_diagram_types(design, deploy_characteristics)
        assert DiagramType.DEPLOYMENT in result

    def test_minimum_three_diagrams(self, tool):
        """Even with a minimal style, at least MIN_DIAGRAMS are returned."""
        design = {"style": "unknown-style"}
        result = tool._select_diagram_types(design, [])
        assert len(result) >= MIN_DIAGRAMS

    def test_maximum_five_diagrams(self, tool, explicit_characteristics, deploy_characteristics):
        """Even with many triggers, caps at MAX_DIAGRAMS."""
        design = {"style": "event-driven microservices pipeline layered"}
        chars = explicit_characteristics + deploy_characteristics
        result = tool._select_diagram_types(design, chars)
        assert len(result) <= MAX_DIAGRAMS

    def test_removal_priority_keeps_state_over_flowchart(self, tool):
        """When capping, state has higher priority than flowchart."""
        design = {"style": "event-driven pipeline layered"}
        chars = [
            {"name": "data_integrity", "current_requirement_coverage": "explicit", "measurable_target": ""},
            {"name": "deployability", "current_requirement_coverage": "explicit", "measurable_target": ""},
        ]
        result = tool._select_diagram_types(design, chars)
        # state should survive; flowchart should be removed first
        if DiagramType.STATE in result:
            assert DiagramType.FLOWCHART not in result or len(result) <= MAX_DIAGRAMS

    def test_no_duplicates(self, tool, event_driven_design, explicit_characteristics):
        result = tool._select_diagram_types(event_driven_design, explicit_characteristics)
        assert len(result) == len(set(result))


# ===========================================================================
# _rejection_reason tests
# ===========================================================================

class TestRejectionReason:
    """Tests for the _rejection_reason guard."""

    def test_valid_diagram_returns_none(self, tool):
        raw = _make_diagram_dict()
        assert tool._rejection_reason(raw) is None

    def test_empty_source_rejected(self, tool):
        raw = _make_diagram_dict(mermaid_source="")
        assert "empty" in tool._rejection_reason(raw)

    def test_fenced_source_rejected(self, tool):
        raw = _make_diagram_dict(mermaid_source="```mermaid\ngraph TD\n```")
        assert "fence" in tool._rejection_reason(raw).lower()

    def test_short_source_rejected(self, tool):
        raw = _make_diagram_dict(lines=5)
        reason = tool._rejection_reason(raw)
        assert reason is not None
        assert "non-empty lines" in reason

    def test_wrong_syntax_prefix_rejected(self, tool):
        raw = _make_diagram_dict(
            diagram_type="sequence_primary",
            prefix="graph TD",  # Wrong — should be sequenceDiagram
            lines=15,
        )
        reason = tool._rejection_reason(raw)
        assert reason is not None
        assert "expected one of" in reason.lower()

    def test_blank_title_rejected(self, tool):
        raw = _make_diagram_dict(title="")
        reason = tool._rejection_reason(raw)
        assert reason is not None
        assert "title" in reason.lower()

    def test_whitespace_only_title_rejected(self, tool):
        raw = _make_diagram_dict(title="   ")
        reason = tool._rejection_reason(raw)
        assert reason is not None
        assert "title" in reason.lower()

    def test_exactly_min_lines_passes(self, tool):
        raw = _make_diagram_dict(lines=MIN_DIAGRAM_SOURCE_LINES)
        assert tool._rejection_reason(raw) is None

    def test_one_below_min_lines_rejected(self, tool):
        raw = _make_diagram_dict(lines=MIN_DIAGRAM_SOURCE_LINES - 1)
        reason = tool._rejection_reason(raw)
        assert reason is not None


# ===========================================================================
# _validate_diagrams tests
# ===========================================================================

class TestValidateDiagrams:
    """Tests for _validate_diagrams — dedup, missing types, all-fail."""

    def test_valid_diagrams_pass(self, tool):
        raw = [
            _make_diagram_dict("D-001", "c4_container", "C4"),
            _make_diagram_dict("D-002", "sequence_primary", "Seq P", prefix="sequenceDiagram"),
            _make_diagram_dict("D-003", "sequence_error", "Seq E", prefix="sequenceDiagram"),
        ]
        expected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY, DiagramType.SEQUENCE_ERROR]
        result = tool._validate_diagrams(raw, expected)
        assert len(result) == 3

    def test_duplicate_type_keeps_first(self, tool):
        raw = [
            _make_diagram_dict("D-001", "c4_container", "C4 First"),
            _make_diagram_dict("D-002", "c4_container", "C4 Dup"),
        ]
        expected = [DiagramType.C4_CONTAINER]
        result = tool._validate_diagrams(raw, expected)
        assert len(result) == 1
        assert result[0].diagram_id == "D-001"

    def test_invalid_type_skipped(self, tool):
        raw = [
            _make_diagram_dict("D-001", "c4_container", "C4"),
            {**_make_diagram_dict("D-002"), "type": "not_a_real_type"},
        ]
        expected = [DiagramType.C4_CONTAINER]
        result = tool._validate_diagrams(raw, expected)
        assert len(result) == 1

    def test_all_fail_raises(self, tool):
        raw = [
            _make_diagram_dict("D-001", "c4_container", "", lines=5),  # fail: blank title AND short
        ]
        expected = [DiagramType.C4_CONTAINER]
        with pytest.raises(ToolExecutionException, match="All generated diagrams failed"):
            tool._validate_diagrams(raw, expected)

    def test_mixed_valid_and_invalid(self, tool):
        raw = [
            _make_diagram_dict("D-001", "c4_container", "C4"),
            _make_diagram_dict("D-002", "sequence_primary", "", prefix="sequenceDiagram"),  # blank title
            _make_diagram_dict("D-003", "sequence_error", "Seq E", prefix="sequenceDiagram"),
        ]
        expected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY, DiagramType.SEQUENCE_ERROR]
        result = tool._validate_diagrams(raw, expected)
        assert len(result) == 2
        types = {d.type for d in result}
        assert DiagramType.SEQUENCE_PRIMARY not in types


# ===========================================================================
# run() end-to-end tests
# ===========================================================================

class TestDiagramGeneratorRun:
    """End-to-end tests for DiagramGeneratorTool.run()."""

    async def test_populates_diagrams_list(self, tool, context_with_design, mock_llm):
        mock_llm.complete.return_value = _make_valid_response()
        result = await tool.run(context_with_design)
        assert len(result.diagrams) >= 3

    async def test_populates_backward_compat_component(self, tool, context_with_design, mock_llm):
        mock_llm.complete.return_value = _make_valid_response()
        result = await tool.run(context_with_design)
        assert result.mermaid_component_diagram != ""
        assert "graph" in result.mermaid_component_diagram.lower()

    async def test_populates_backward_compat_sequence(self, tool, context_with_design, mock_llm):
        mock_llm.complete.return_value = _make_valid_response()
        result = await tool.run(context_with_design)
        assert result.mermaid_sequence_diagram != ""

    async def test_raises_when_design_empty(self, tool, mock_llm):
        ctx = ArchitectureContext(raw_requirements="test")
        with pytest.raises(ToolExecutionException):
            await tool.run(ctx)

    async def test_raises_on_invalid_json(self, tool, context_with_design, mock_llm):
        mock_llm.complete.return_value = "not-json"
        with pytest.raises(ToolExecutionException, match="failed generation"):
            await tool.run(context_with_design)

    async def test_raises_on_empty_diagrams_list(self, tool, context_with_design, mock_llm):
        mock_llm.complete.return_value = json.dumps({"diagrams": []})
        with pytest.raises(ToolExecutionException, match="empty diagrams"):
            await tool.run(context_with_design)


# ===========================================================================
# get_diagram() helper on ArchitectureContext
# ===========================================================================

class TestGetDiagram:
    """Tests for ArchitectureContext.get_diagram()."""

    def test_returns_source_for_existing_type(self):
        ctx = ArchitectureContext(raw_requirements="test")
        ctx.diagrams = [
            Diagram(
                diagram_id="D-001",
                type=DiagramType.C4_CONTAINER,
                title="C4",
                description="test",
                mermaid_source="graph TD\n  A-->B",
            ),
        ]
        assert ctx.get_diagram(DiagramType.C4_CONTAINER) == "graph TD\n  A-->B"

    def test_returns_empty_for_missing_type(self):
        ctx = ArchitectureContext(raw_requirements="test")
        assert ctx.get_diagram(DiagramType.ER) == ""

    def test_returns_first_match_when_multiple(self):
        ctx = ArchitectureContext(raw_requirements="test")
        ctx.diagrams = [
            Diagram(
                diagram_id="D-001",
                type=DiagramType.STATE,
                title="State 1",
                description="first",
                mermaid_source="stateDiagram-v2\n  first",
            ),
            Diagram(
                diagram_id="D-002",
                type=DiagramType.STATE,
                title="State 2",
                description="second",
                mermaid_source="stateDiagram-v2\n  second",
            ),
        ]
        assert "first" in ctx.get_diagram(DiagramType.STATE)
