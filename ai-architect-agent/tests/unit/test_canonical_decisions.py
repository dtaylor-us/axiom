"""Tests for canonical buy/adopt decision propagation."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models import ArchitectureContext
from app.tools.architecture_generator import ArchitectureGeneratorTool
from app.tools.fmea_analyzer import FMEAPlusTool


def _decision(recommendation: str) -> dict:
    """Build a representative buy-vs-build decision."""
    return {
        "component_name": "Payment Processing",
        "recommendation": recommendation,
        "recommended_solution": "Stripe",
        "rationale": "Stripe covers the payment compliance surface.",
    }


def _architecture_response() -> str:
    """Return a valid architecture generator response."""
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
            "selection_rationale": "Service-based best balances the stated scalability and delivery characteristics while avoiding microservice operational overhead for this team.",
        },
        "style": "Service-based",
        "components": [
            {"name": "API", "type": "service"},
            {"name": "Stripe", "type": "external"},
        ],
        "interactions": [
            {
                "from": "API",
                "to": "Stripe",
                "protocol": "REST",
                "purpose": "Authorizes payment transactions.",
            }
        ],
        "when_to_reconsider_this_style": ["Independent scaling pressure"],
    })


def test_canonical_decisions_empty_when_no_decisions() -> None:
    """canonical_decisions returns an empty list without BVB decisions."""
    context = ArchitectureContext()

    assert context.canonical_decisions == []


@pytest.mark.parametrize("recommendation", ["buy", "adopt", "BUY", "ADOPT"])
def test_canonical_decisions_include_buy_and_adopt(
    recommendation: str,
) -> None:
    """canonical_decisions returns entries for buy and adopt decisions."""
    context = ArchitectureContext(
        buy_vs_build_analysis=[_decision(recommendation)]
    )

    assert context.canonical_decisions[0]["component"] == "Payment Processing"


def test_canonical_decisions_exclude_build() -> None:
    """canonical_decisions does not return build recommendations."""
    context = ArchitectureContext(buy_vs_build_analysis=[_decision("build")])

    assert context.canonical_decisions == []


def test_canonical_decision_constraint_contains_do_not_design() -> None:
    """canonical_decisions constraint field forbids internal implementation."""
    context = ArchitectureContext(buy_vs_build_analysis=[_decision("buy")])

    assert "Do NOT generate any internal service" in context.canonical_decisions[0]["constraint"]


def test_has_canonical_decisions_false_without_decisions() -> None:
    """has_canonical_decisions returns False with no decisions."""
    assert ArchitectureContext().has_canonical_decisions is False


def test_has_canonical_decisions_true_with_buy_decision() -> None:
    """has_canonical_decisions returns True with buy/adopt decisions."""
    context = ArchitectureContext(buy_vs_build_analysis=[_decision("adopt")])

    assert context.has_canonical_decisions is True


@pytest.mark.asyncio
async def test_architecture_generator_passes_canonical_decisions() -> None:
    """ArchitectureGeneratorTool passes canonical_decisions to the prompt."""
    llm = AsyncMock()
    llm.complete.return_value = _architecture_response()
    memory = AsyncMock()
    memory.retrieve_similar = AsyncMock(return_value=[])
    tool = ArchitectureGeneratorTool(llm, memory)
    context = ArchitectureContext(
        characteristics=[{"name": "scalability"}],
        buy_vs_build_analysis=[_decision("buy")],
    )

    with patch("app.tools.architecture_generator.load_prompt", return_value="prompt") as loader:
        await tool.run(context)

    assert loader.call_args.kwargs["canonical_decisions"]


@pytest.mark.asyncio
async def test_fmea_passes_canonical_decisions() -> None:
    """FMEAPlusTool passes canonical_decisions to the prompt."""
    llm = AsyncMock()
    llm.complete.return_value = json.dumps({"fmea_risks": []})
    tool = FMEAPlusTool(llm)
    context = ArchitectureContext(
        architecture_design={"components": [{"name": "Stripe", "type": "external"}]},
        buy_vs_build_analysis=[_decision("buy")],
    )

    with patch("app.tools.fmea_analyzer.load_prompt", return_value="prompt") as loader:
        await tool.run(context)

    assert loader.call_args.kwargs["canonical_decisions"]
