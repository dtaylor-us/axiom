"""Tests for architecture interaction contract enforcement."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock

import pytest

from app.models import ArchitectureContext
from app.tools.architecture_generator import ArchitectureGeneratorTool


def _tool() -> ArchitectureGeneratorTool:
    """Create a tool with mocked dependencies."""
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    return ArchitectureGeneratorTool(AsyncMock(), memory)


def _interaction(protocol: str = "REST", purpose: str = "Reads orders") -> dict:
    """Build an interaction object."""
    return {
        "from": "API",
        "to": "Orders",
        "protocol": protocol,
        "purpose": purpose,
    }


def _architecture_response() -> str:
    """Return a response with one valid and one invalid interaction."""
    styles = [
        "Layered",
        "Modular monolith",
        "Microkernel",
        "Pipeline",
        "Service-based",
        "Event-driven",
        "Microservices",
        "Space-based",
    ]
    return json.dumps({
        "style_selection": {
            "style_scores": [{"style": s, "score": 1, "vetoed": False} for s in styles],
            "selected_style": "Service-based",
            "runner_up": "Layered",
            "selection_rationale": "Service-based is selected because the system needs independently deployable coarse-grained services without microservice operational overhead.",
        },
        "style": "Service-based",
        "components": [{"name": "API", "type": "service"}],
        "interactions": [_interaction(), _interaction(protocol="undefined")],
        "when_to_reconsider_this_style": ["Team grows"],
    })


def test_validate_interactions_rejects_undefined_protocol() -> None:
    """_validate_interactions rejects protocol='undefined'."""
    assert _tool()._validate_interactions([_interaction(protocol="undefined")]) == []


def test_validate_interactions_rejects_empty_protocol() -> None:
    """_validate_interactions rejects empty protocol."""
    assert _tool()._validate_interactions([_interaction(protocol="")]) == []


def test_validate_interactions_rejects_undefined_purpose() -> None:
    """_validate_interactions rejects purpose='undefined'."""
    assert _tool()._validate_interactions([_interaction(purpose="undefined")]) == []


def test_validate_interactions_accepts_valid_interaction() -> None:
    """_validate_interactions accepts REST with non-empty purpose."""
    result = _tool()._validate_interactions([_interaction()])

    assert result == [_interaction()]


def test_validate_interactions_logs_warning_for_rejection(caplog) -> None:
    """_validate_interactions logs a warning for each rejection."""
    with caplog.at_level(logging.WARNING):
        _tool()._validate_interactions([_interaction(protocol="undefined")])

    assert any("undefined protocol" in record.message for record in caplog.records)


def test_validate_interactions_returns_only_valid_items() -> None:
    """_validate_interactions returns only valid interactions."""
    result = _tool()._validate_interactions([
        _interaction(),
        _interaction(protocol="null"),
    ])

    assert result == [_interaction()]


@pytest.mark.asyncio
async def test_run_writes_only_valid_interactions_to_context() -> None:
    """ArchitectureGeneratorTool writes only validated interactions."""
    tool = _tool()
    tool.llm_client.complete.return_value = _architecture_response()
    context = ArchitectureContext(characteristics=[{"name": "deployability"}])

    result = await tool.run(context)

    assert result.architecture_design["interactions"] == [_interaction()]
