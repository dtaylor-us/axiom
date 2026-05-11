"""Tests for DiagramGeneratorTool per-type sequential generation.

Covers ADL diagram_generation_per_type: one LLM call per diagram type,
partial success preference, and all-fail exception.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.context import ArchitectureContext, DiagramType
from app.tools.base import ToolExecutionException
from app.tools.diagram_generator import DiagramGeneratorTool


SAMPLE_ARCHITECTURE_DESIGN = {
    "style": "microservices",
    "components": [{"name": "PaymentService", "type": "service"}],
    "interactions": [],
}

SAMPLE_CHARACTERISTICS = [
    {"name": "scalability", "current_requirement_coverage": "explicit", "measurable_target": "10k TPS"},
]


def _make_valid_diagram_response(diagram_type: str) -> str:
    """Return a valid single-diagram JSON response for the given type."""
    if diagram_type in ("c4_container", "deployment"):
        source_lines = "\n".join(["graph TD", "A[Client]", "B[API]", "C[(DB)]",
                                  "A-->B", "B-->C", "D[Cache]", "B-->D",
                                  "E[Queue]", "B-->E", "F[Worker]", "E-->F"])
    elif diagram_type.startswith("sequence"):
        source_lines = "\n".join(["sequenceDiagram", "Client->>API: POST /pay",
                                  "activate API", "API->>PaySvc: process(req)",
                                  "activate PaySvc", "PaySvc->>DB: insert txn",
                                  "DB-->>PaySvc: txn_id", "PaySvc-->>API: ok",
                                  "deactivate PaySvc", "API-->>Client: 201"])
    elif diagram_type == "state":
        source_lines = "\n".join(["stateDiagram-v2", "[*]-->Pending",
                                  "Pending-->Processing", "Processing-->Completed",
                                  "Processing-->Failed", "Failed-->[*]",
                                  "Completed-->[*]", "note right of Processing: validates card",
                                  "Pending-->Cancelled", "Cancelled-->[*]"])
    else:
        source_lines = "\n".join(["classDiagram", "class Payment {",
                                  "  +String id", "  +Decimal amount",
                                  "  +Status status", "  +process()", "}",
                                  "class Transaction {", "  +String txnId", "}",
                                  "Payment --o Transaction"])

    return json.dumps({
        "type": diagram_type,
        "title": f"Test {diagram_type} diagram",
        "description": "Test description",
        "mermaid_source": source_lines,
        "characteristic_addressed": "scalability",
    })


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.complete = AsyncMock()
    return llm


@pytest.fixture
def tool(mock_llm):
    return DiagramGeneratorTool(llm_client=mock_llm)


@pytest.fixture
def base_ctx():
    ctx = ArchitectureContext(
        conversation_id="test-diag",
        raw_requirements="Build a payment system",
    )
    ctx.architecture_design = SAMPLE_ARCHITECTURE_DESIGN
    ctx.characteristics = SAMPLE_CHARACTERISTICS
    return ctx


class TestPerTypeGeneration:
    """DiagramGeneratorTool calls _generate_single_diagram per selected type."""

    async def test_generate_single_diagram_called_per_type(self, tool, mock_llm, base_ctx):
        """llm_client.complete() is called once per selected diagram type."""
        selected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY, DiagramType.SEQUENCE_ERROR]

        def _response(prompt, **kwargs):
            # Detect diagram type from prompt and return valid response
            for dt in selected:
                if dt.value in prompt:
                    return _make_valid_diagram_response(dt.value)
            return _make_valid_diagram_response("c4_container")

        mock_llm.complete.side_effect = _response

        with patch.object(tool, "_select_diagram_types", return_value=selected):
            with patch("app.tools.diagram_generator.load_prompt", side_effect=lambda name, **kw: kw.get("diagram_type", "c4_container")):
                result = await tool.run(base_ctx)

        assert mock_llm.complete.call_count == len(selected)
        assert len(result.diagrams) == len(selected)

    async def test_partial_success_returns_valid_diagrams(self, tool, mock_llm, base_ctx):
        """When some types fail, the tool returns only the valid ones (no exception)."""
        selected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY, DiagramType.SEQUENCE_ERROR]

        call_count = 0
        def _response(prompt, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return "NOT JSON AT ALL {{{{"  # second call fails
            dt = selected[call_count - 1].value
            return _make_valid_diagram_response(dt)

        mock_llm.complete.side_effect = _response

        with patch.object(tool, "_select_diagram_types", return_value=selected):
            with patch("app.tools.diagram_generator.load_prompt", side_effect=lambda name, **kw: kw.get("diagram_type", "c4_container")):
                with patch.object(tool, "attempt_repair", side_effect=ToolExecutionException("repair failed")):
                    result = await tool.run(base_ctx)

        # Should return the successful diagrams, not raise
        assert len(result.diagrams) >= 1

    async def test_all_fail_raises_tool_execution_exception(self, tool, mock_llm, base_ctx):
        """When every diagram type fails, ToolExecutionException is raised."""
        selected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY]

        mock_llm.complete.side_effect = Exception("LLM completely down")

        with patch.object(tool, "_select_diagram_types", return_value=selected):
            with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
                with pytest.raises(ToolExecutionException, match="All diagram types failed"):
                    await tool.run(base_ctx)

    async def test_empty_architecture_design_raises_immediately(self, tool, base_ctx):
        """run() raises ToolExecutionException if architecture_design is empty."""
        base_ctx.architecture_design = {}
        with pytest.raises(ToolExecutionException, match="architecture design"):
            await tool.run(base_ctx)

    async def test_compat_fields_populated_from_diagrams(self, tool, mock_llm, base_ctx):
        """mermaid_component_diagram and mermaid_sequence_diagram are set after run()."""
        selected = [DiagramType.C4_CONTAINER, DiagramType.SEQUENCE_PRIMARY]

        def _response(prompt, **kwargs):
            for dt in selected:
                if dt.value in str(prompt):
                    return _make_valid_diagram_response(dt.value)
            return _make_valid_diagram_response("c4_container")

        mock_llm.complete.side_effect = _response

        with patch.object(tool, "_select_diagram_types", return_value=selected):
            with patch("app.tools.diagram_generator.load_prompt", side_effect=lambda name, **kw: kw.get("diagram_type", "c4_container")):
                result = await tool.run(base_ctx)

        # Compat fields should be populated
        assert result.mermaid_component_diagram is not None or result.diagrams


class TestGenerateSingleDiagram:
    """Unit tests for the _generate_single_diagram() method."""

    async def test_returns_none_when_llm_raises(self, tool, mock_llm, base_ctx):
        """_generate_single_diagram returns None when llm_client.complete() raises."""
        mock_llm.complete.side_effect = Exception("network error")

        with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
            result = await tool._generate_single_diagram(DiagramType.C4_CONTAINER, base_ctx)

        assert result is None

    async def test_returns_none_when_source_fails_validation(self, tool, mock_llm, base_ctx):
        """_generate_single_diagram returns None when diagram source is too short."""
        mock_llm.complete.return_value = json.dumps({
            "type": "c4_container",
            "title": "Tiny",
            "description": "x",
            "mermaid_source": "graph TD\nA-->B",  # only 2 lines — below minimum
            "characteristic_addressed": "scalability",
        })

        with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
            result = await tool._generate_single_diagram(DiagramType.C4_CONTAINER, base_ctx)

        assert result is None

    async def test_returns_diagram_on_valid_response(self, tool, mock_llm, base_ctx):
        """_generate_single_diagram returns a Diagram instance on valid LLM response."""
        mock_llm.complete.return_value = _make_valid_diagram_response("c4_container")

        with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
            result = await tool._generate_single_diagram(DiagramType.C4_CONTAINER, base_ctx)

        assert result is not None
        assert result.type == DiagramType.C4_CONTAINER

    async def test_schema_is_passed_to_complete(self, tool, mock_llm, base_ctx):
        """_generate_single_diagram passes output_schema and schema_name to complete()."""
        from app.llm.schemas import SCHEMAS
        mock_llm.complete.return_value = _make_valid_diagram_response("c4_container")

        with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
            await tool._generate_single_diagram(DiagramType.C4_CONTAINER, base_ctx)

        _, kwargs = mock_llm.complete.call_args
        assert kwargs.get("output_schema") == SCHEMAS.get("diagram_generation_single")
        assert kwargs.get("schema_name") == "diagram_generation_single"
