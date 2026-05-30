"""Tests for ADL generation from canonical sourcing decisions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.models import ArchitectureContext
from app.tools.adl_generator import ADLGeneratorV2Tool


def _adl_block(adl_id: str, capability: str) -> dict:
    """Build a valid ADL block for a sourcing capability."""
    return {
        "adl_id": adl_id,
        "metadata": {
            "requires": "PyTestArch Python library",
            "description": f"Assert no internal {capability} implementation.",
            "prompt": f"Write a test verifying {capability} delegates externally.",
        },
        "adl_source": (
            "DEFINE SYSTEM IAM Platform AS app\n"
            "  DEFINE SERVICE InternalServices AS app.services\n"
            f"  DEFINE COMPONENT {capability}CustomImplementation AS app.custom\n"
            f"ASSERT(InternalServices has NO DEPENDENCY ON "
            f"{capability}CustomImplementation)"
        ),
        "characteristic_enforced": "security",
        "enforcement_level": "hard",
    }


def _response(count: int) -> str:
    """Return a valid ADL response with the requested block count."""
    capabilities = ["Authentication", "SSO", "MFA", "Boundary", "Data"]
    return json.dumps([
        _adl_block(f"ADL-{index:03d}", capabilities[index - 1])
        for index in range(1, count + 1)
    ])


def _context() -> ArchitectureContext:
    """Return architecture context with two sourcing decisions."""
    return ArchitectureContext(
        parsed_entities={"domain": "iam"},
        architecture_design={
            "components": [
                {"name": "Okta Integration", "type": "external"},
                {"name": "Ping Integration", "type": "external"},
                {"name": "Profile Service", "type": "service"},
            ]
        },
        characteristics=[{"name": "security"}],
        buy_vs_build_analysis=[
            {
                "component_name": "Authentication",
                "recommendation": "buy",
                "recommended_solution": "Okta",
            },
            {
                "component_name": "SSO",
                "recommendation": "buy",
                "recommended_solution": "Ping Identity",
            },
        ],
    )


@pytest.mark.asyncio
async def test_adl_generator_receives_canonical_decisions_in_prompt() -> None:
    """adl_generator receives canonical_decisions in prompt."""
    llm = AsyncMock()
    llm.complete.return_value = _response(count=5)
    tool = ADLGeneratorV2Tool(llm)

    await tool.run(_context())

    prompt = llm.complete.call_args.args[0]
    assert "MANDATORY ADL BLOCKS FROM SOURCING DECISIONS" in prompt
    assert "Authentication" in prompt
    assert "Ping Identity" in prompt


@pytest.mark.asyncio
async def test_adl_generator_produces_n_plus_three_minimum_blocks() -> None:
    """adl_generator produces N+3 minimum blocks for N canonical decisions."""
    llm = AsyncMock()
    llm.complete.return_value = _response(count=5)
    tool = ADLGeneratorV2Tool(llm)

    result = await tool.run(_context())

    assert len(result.adl_blocks) == 5


@pytest.mark.asyncio
async def test_each_canonical_decision_produces_one_adl_block() -> None:
    """each canonical decision produces one ADL block."""
    llm = AsyncMock()
    llm.complete.return_value = _response(count=5)
    tool = ADLGeneratorV2Tool(llm)

    result = await tool.run(_context())
    descriptions = [
        block.metadata.description for block in result.adl_blocks
    ]

    assert any("Authentication" in description for description in descriptions)
    assert any("SSO" in description for description in descriptions)
