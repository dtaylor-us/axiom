"""IAM acceptance coverage for binding sourcing decisions."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.models import ArchitectureContext
from app.review.nodes import calculate_consistency_bonus
from app.tools.adl_generator import ADLGeneratorV2Tool
from app.tools.architecture_generator import ArchitectureGeneratorTool


def _architecture_response_with_custom_iam_services() -> str:
    """Return a deliberately violating IAM architecture response."""
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
            "runner_up": "Event-driven",
            "selection_rationale": (
                "Service-based architecture is selected because IAM requires "
                "clear service boundaries, auditability, and operational "
                "simplicity while still allowing independent scaling of "
                "profile and policy capabilities."
            ),
        },
        "style": "Service-based",
        "components": [
            {
                "name": "Authentication Service",
                "type": "service",
                "responsibility": "Implements authentication.",
                "technology": "Python",
            },
            {
                "name": "SSO Service",
                "type": "service",
                "responsibility": "Implements SSO.",
                "technology": "Python",
            },
            {
                "name": "MFA Service",
                "type": "service",
                "responsibility": "Implements MFA.",
                "technology": "Python",
            },
            {
                "name": "Access Policy Service",
                "type": "service",
                "responsibility": "Evaluates authorization policies.",
                "technology": "Python",
            },
        ],
        "interactions": [
            {
                "from": "Access Policy Service",
                "to": "Authentication Service",
                "protocol": "REST",
                "purpose": "Checks session state.",
            }
        ],
        "when_to_reconsider_this_style": ["Global latency exceeds target."],
    })


def _adl_response() -> str:
    """Return six ADL blocks, three sourcing and three structural."""
    capabilities = [
        "Authentication",
        "SSO",
        "MFA",
        "Boundary",
        "Data",
        "Security",
    ]
    return json.dumps([
        {
            "adl_id": f"ADL-{index:03d}",
            "metadata": {
                "requires": "PyTestArch Python library",
                "description": f"Assert no internal {capability} implementation.",
                "prompt": f"Write a test verifying {capability} is enforced.",
            },
            "adl_source": (
                "DEFINE SYSTEM IAM Platform AS app\n"
                "  DEFINE SERVICE InternalServices AS app.services\n"
                f"  DEFINE COMPONENT {capability}CustomImplementation AS app.custom\n"
                "ASSERT(InternalServices has NO DEPENDENCY ON "
                f"{capability}CustomImplementation)"
            ),
            "characteristic_enforced": "security",
            "enforcement_level": "hard",
        }
        for index, capability in enumerate(capabilities, start=1)
    ])


def _iam_context() -> ArchitectureContext:
    """Return the IAM buy-oriented pipeline context."""
    return ArchitectureContext(
        conversation_id="iam-acceptance",
        raw_requirements="Enterprise IAM with authentication, SSO, and MFA.",
        parsed_entities={"domain": "iam", "system_type": "identity platform"},
        characteristics=[{"name": "security"}, {"name": "auditability"}],
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
            {
                "component_name": "MFA",
                "recommendation": "buy",
                "recommended_solution": "Duo",
            },
        ],
    )


@pytest.mark.asyncio
async def test_iam_buy_decisions_remove_custom_auth_services() -> None:
    """IAM buy decisions remove custom auth, SSO, and MFA services."""
    architecture_llm = AsyncMock()
    architecture_llm.complete.return_value = _architecture_response_with_custom_iam_services()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    architecture_tool = ArchitectureGeneratorTool(architecture_llm, memory)
    context = await architecture_tool.run(_iam_context())

    components = context.architecture_design["components"]
    component_names = {component["name"] for component in components}
    assert "Authentication Service" not in component_names
    assert "SSO Service" not in component_names
    assert "MFA Service" not in component_names

    bought_components = {
        component["name"]: component
        for component in components
        if component.get("ownership") == "bought-saas"
    }
    assert bought_components["Okta Integration"]["type"] == "external"
    assert bought_components["Ping Identity Integration"]["type"] == "external"
    assert bought_components["Duo Integration"]["type"] == "external"
    assert calculate_consistency_bonus(
        context.buy_vs_build_analysis,
        context.architecture_design,
    ) == 6


@pytest.mark.asyncio
async def test_iam_sourcing_decisions_generate_required_adl_blocks() -> None:
    """IAM sourcing decisions generate at least six ADL blocks."""
    architecture_llm = AsyncMock()
    architecture_llm.complete.return_value = _architecture_response_with_custom_iam_services()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    context = await ArchitectureGeneratorTool(
        architecture_llm,
        memory,
    ).run(_iam_context())

    adl_llm = AsyncMock()
    adl_llm.complete.return_value = _adl_response()
    context = await ADLGeneratorV2Tool(adl_llm).run(context)

    descriptions = [block.metadata.description for block in context.adl_blocks]
    assert len(context.adl_blocks) >= 6
    assert any("Authentication" in description for description in descriptions)
    assert any("SSO" in description for description in descriptions)
    assert any("MFA" in description for description in descriptions)
