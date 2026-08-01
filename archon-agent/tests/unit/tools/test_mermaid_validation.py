"""Tests for Mermaid validation and repair."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.context import ArchitectureContext, DiagramType
from app.tools.diagram_generator import DiagramGeneratorTool


def _valid_source() -> str:
    """Return valid graph TD source with enough detail."""
    return "\n".join([
        "graph TD",
        "A[Client] -->|REST| B[API]",
        "B -->|SQL| C[(Database)]",
        "B -->|AMQP| D[Queue]",
        "D -->|Event| E[Worker]",
        "E -->|REST| F[External API]",
        "B -->|Cache read| G[(Redis)]",
        "G -->|Hit| B",
        "E -->|Write| C",
        "F -->|Response| E",
    ])


def _response(source: str) -> str:
    """Wrap Mermaid source as a single diagram JSON response."""
    return json.dumps({
        "type": "c4_container",
        "title": "Container View",
        "description": "Shows the runtime containers.",
        "mermaid_source": source,
        "characteristic_addressed": "scalability",
    })


@pytest.fixture
def tool() -> DiagramGeneratorTool:
    """Create a diagram tool with a mocked LLM."""
    return DiagramGeneratorTool(AsyncMock())


def test_validate_mermaid_syntax_accepts_valid_graph(tool) -> None:
    """_validate_mermaid_syntax returns True for valid graph TD."""
    assert tool._validate_mermaid_syntax(_valid_source(), DiagramType.C4_CONTAINER) == (True, "")


def test_validate_mermaid_syntax_rejects_empty_source(tool) -> None:
    """_validate_mermaid_syntax returns False for empty source."""
    valid, error = tool._validate_mermaid_syntax("", DiagramType.C4_CONTAINER)

    assert valid is False
    assert error == "Empty Mermaid source"


def test_validate_mermaid_syntax_rejects_wrong_opening(tool) -> None:
    """_validate_mermaid_syntax returns False for wrong opening."""
    valid, error = tool._validate_mermaid_syntax(_valid_source().replace("graph TD", "sequenceDiagram"), DiagramType.C4_CONTAINER)

    assert valid is False
    assert "Wrong opening" in error


def test_validate_mermaid_syntax_rejects_undefined_edge_label(tool) -> None:
    """_validate_mermaid_syntax rejects undefined in an edge context."""
    source = _valid_source().replace("|REST|", "|undefined|", 1)

    valid, error = tool._validate_mermaid_syntax(source, DiagramType.C4_CONTAINER)

    assert valid is False
    assert "undefined" in error


def test_validate_mermaid_syntax_rejects_unquoted_parentheses(tool) -> None:
    """_validate_mermaid_syntax rejects unquoted parentheses in edge labels."""
    source = _valid_source().replace("|REST|", "|REST (sync)|", 1)

    valid, error = tool._validate_mermaid_syntax(source, DiagramType.C4_CONTAINER)

    assert valid is False
    assert "Unquoted parentheses" in error


@pytest.mark.asyncio
async def test_generate_single_diagram_repairs_invalid_source(tool) -> None:
    """_generate_single_diagram attempts repair on syntax failure."""
    invalid = _valid_source().replace("|REST|", "|REST (sync)|", 1)
    tool.llm_client.complete.side_effect = [_response(invalid), _valid_source()]

    with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
        result = await tool._generate_single_diagram(
            DiagramType.C4_CONTAINER,
            ArchitectureContext(architecture_design={"components": []}),
        )

    assert result is not None
    assert result.has_syntax_error is False
    assert tool.llm_client.complete.call_count == 2


@pytest.mark.asyncio
async def test_generate_single_diagram_stores_error_when_repair_fails(tool) -> None:
    """_generate_single_diagram stores has_syntax_error=True after failed repair."""
    invalid = _valid_source().replace("|REST|", "|REST (sync)|", 1)
    tool.llm_client.complete.side_effect = [_response(invalid), invalid]

    with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
        result = await tool._generate_single_diagram(
            DiagramType.C4_CONTAINER,
            ArchitectureContext(architecture_design={"components": []}),
        )

    assert result is not None
    assert result.has_syntax_error is True
    assert result.syntax_error_description


@pytest.mark.asyncio
async def test_generate_single_diagram_marks_valid_diagram_clean(tool) -> None:
    """_generate_single_diagram stores has_syntax_error=False for valid diagrams."""
    tool.llm_client.complete.return_value = _response(_valid_source())

    with patch("app.tools.diagram_generator.load_prompt", return_value="prompt"):
        result = await tool._generate_single_diagram(
            DiagramType.C4_CONTAINER,
            ArchitectureContext(architecture_design={"components": []}),
        )

    assert result is not None
    assert result.has_syntax_error is False
