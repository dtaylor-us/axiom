"""Tests for architecture generation sourcing and ownership enforcement."""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.models import ArchitectureContext
from app.tools.architecture_generator import ArchitectureGeneratorTool


def _response_with_auth_service() -> str:
    """Return an architecture response that violates auth sourcing."""
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
            "style_scores": [
                {"style": style, "score": index, "vetoed": False}
                for index, style in enumerate(styles, start=1)
            ],
            "selected_style": "Service-based",
            "runner_up": "Modular monolith",
            "selection_rationale": (
                "Service-based architecture is selected because it balances "
                "security boundaries, operability, and scale without the "
                "operational overhead of microservices for this IAM domain."
            ),
        },
        "style": "Service-based",
        "components": [
            {
                "name": "Authentication Service",
                "type": "service",
                "responsibility": "Implements authentication workflows.",
                "technology": "Python",
            },
            {
                "name": "User Profile Service",
                "type": "service",
                "responsibility": "Owns profile data.",
                "technology": "Python",
            },
        ],
        "interactions": [
            {
                "from": "User Profile Service",
                "to": "Authentication Service",
                "protocol": "REST",
                "purpose": "Checks user authentication state.",
            }
        ],
        "when_to_reconsider_this_style": ["Tenant count exceeds limits."],
    })


def _context() -> ArchitectureContext:
    """Return context with an Okta buy decision."""
    return ArchitectureContext(
        raw_requirements="IAM platform",
        characteristics=[{"name": "security"}],
        buy_vs_build_analysis=[{
            "component_name": "Authentication",
            "recommendation": "buy",
            "recommended_solution": "Okta",
            "rationale": "Use proven identity provider.",
        }],
    )


@pytest.mark.asyncio
async def test_architecture_generator_passes_canonical_decisions_to_prompt() -> None:
    """architecture_generator passes canonical_decisions to prompt."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    with patch("app.tools.architecture_generator.load_prompt", return_value="prompt") as loader:
        await tool.run(_context())

    assert loader.call_args.kwargs["canonical_decisions"][0]["component"] == "Authentication"


@pytest.mark.asyncio
async def test_architecture_generator_logs_architecture_gen_audit(caplog) -> None:
    """architecture_generator logs ARCHITECTURE_GEN_AUDIT."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    with caplog.at_level(logging.INFO):
        await tool.run(_context())

    assert "ARCHITECTURE_GEN_AUDIT: canonical_decisions=1" in caplog.text


@pytest.mark.asyncio
async def test_architecture_generator_logs_each_constraint_component(caplog) -> None:
    """architecture_generator logs each constraint component."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    with caplog.at_level(logging.INFO):
        await tool.run(_context())

    assert "constraint component=Authentication decision=buy solution=Okta" in caplog.text


@pytest.mark.asyncio
async def test_ownership_field_present_on_generated_components() -> None:
    """ownership field is present on generated components."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    result = await tool.run(_context())

    assert all(c.get("ownership") for c in result.architecture_design["components"])


@pytest.mark.asyncio
async def test_bought_saas_components_have_type_external() -> None:
    """bought-saas components have type external."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    result = await tool.run(_context())

    bought = [
        c for c in result.architecture_design["components"]
        if c.get("ownership") == "bought-saas"
    ]
    assert bought
    assert all(c.get("type") == "external" for c in bought)


@pytest.mark.asyncio
async def test_excluded_component_patterns_are_passed_to_prompt() -> None:
    """excluded_component_patterns are passed to prompt."""
    llm = AsyncMock()
    llm.complete.return_value = _response_with_auth_service()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)

    with patch("app.tools.architecture_generator.load_prompt", return_value="prompt") as loader:
        await tool.run(_context())

    decision = loader.call_args.kwargs["canonical_decisions"][0]
    assert "authentication" in decision["excluded_component_patterns"]
