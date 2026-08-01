from __future__ import annotations

import asyncio
import logging
from typing import TypedDict

from app.models import ArchitectureContext
from app.review.agent import ArchitectReviewAgent
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Module-level registry — set once during app startup via init_registry()
_registry: dict[str, BaseTool] | None = None

# Module-level review agent — set once during app startup via init_review_agent()
_review_agent: ArchitectReviewAgent | None = None


def init_registry(registry: dict[str, BaseTool]) -> None:
    """Set the module-level tool registry (called once at startup)."""
    global _registry
    _registry = registry


def init_review_agent(agent: ArchitectReviewAgent) -> None:
    """Set the module-level review agent (called once at startup)."""
    global _review_agent
    _review_agent = agent


class PipelineState(TypedDict):
    context: ArchitectureContext


# ---------------------------------------------------------------------------
# Live tool nodes (backed by real LLM calls)
# ---------------------------------------------------------------------------

async def requirement_parsing(state: PipelineState) -> dict:
    ctx = await _registry["requirement_parser"].execute(state["context"])
    return {"context": ctx}


async def requirement_challenge(state: PipelineState) -> dict:
    ctx = await _registry["challenge_engine"].execute(state["context"])
    return {"context": ctx}


async def scenario_modeling(state: PipelineState) -> dict:
    ctx = await _registry["scenario_modeler"].execute(state["context"])
    return {"context": ctx}


# ---------------------------------------------------------------------------
# Stub nodes — placeholders for later phases
# ---------------------------------------------------------------------------

async def _stub_node(state: PipelineState) -> dict:
    """Pass-through stub for stages not yet implemented."""
    await asyncio.sleep(0.05)
    return {"context": state["context"]}


async def characteristic_inference(state: PipelineState) -> dict:
    ctx = await _registry["characteristic_reasoner"].execute(state["context"])
    return {"context": ctx}


async def tactics_recommendation(state: PipelineState) -> dict:
    """Stage 4b — recommends architecture tactics for each inferred quality
    attribute. Runs after characteristic inference and before conflict analysis
    so tactics are available to inform the conflict resolution guidance.
    """
    ctx = await _registry["tactics_advisor"].execute(state["context"])
    return {"context": ctx}


async def conflict_analysis(state: PipelineState) -> dict:
    ctx = await _registry["conflict_analyzer"].execute(state["context"])
    return {"context": ctx}


async def architecture_generation(state: PipelineState) -> dict:
    ctx = await _registry["architecture_generator"].execute(state["context"])
    return {"context": ctx}


async def buy_vs_build_analysis(state: PipelineState) -> dict:
    """
    Stage 6b — evaluates each architecture component for build vs buy vs adopt.

    Runs after architecture_generation so it has the component list, and before
    diagram_generation so diagrams can reflect the chosen solutions.
    """
    ctx = await _registry["buy_vs_build_analyzer"].execute(state["context"])
    return {"context": ctx}


async def diagram_generation(state: PipelineState) -> dict:
    ctx = await _registry["diagram_generator"].execute(state["context"])
    return {"context": ctx}


async def trade_off_analysis(state: PipelineState) -> dict:
    ctx = await _registry["trade_off_engine"].execute(state["context"])
    return {"context": ctx}


async def adl_generation(state: PipelineState) -> dict:
    ctx = await _registry["adl_generator"].execute(state["context"])
    return {"context": ctx}


async def weakness_analysis(state: PipelineState) -> dict:
    ctx = await _registry["weakness_analyzer"].execute(state["context"])
    return {"context": ctx}


async def weakness_and_fmea(state: PipelineState) -> dict:
    """Run weakness analysis followed by FMEA+.

    Weakness must complete before FMEA because the FMEA prompt uses the
    weakness inventory to build cascading failure scenarios. Running the two
    tools in parallel caused FMEA to always receive an empty weakness list,
    silently degrading output quality.

    Sequential execution is the correct behavior here; the performance cost is
    acceptable relative to the quality improvement.
    """
    ctx = state["context"]

    # Weakness must run first so FMEA receives populated ctx.weaknesses.
    ctx = await _registry["weakness_analyzer"].execute(ctx)
    ctx = await _registry["fmea_analyzer"].execute(ctx)

    logger.info(
        "weakness_and_fmea: %d weaknesses, %d FMEA risks (%d critical)",
        len(ctx.weaknesses),
        len(ctx.fmea_risks),
        len(ctx.fmea_critical_risks),
    )
    return {"context": ctx}


async def fmea_analysis(state: PipelineState) -> dict:
    """Standalone FMEA node — kept for backward compatibility."""
    ctx = await _registry["fmea_analyzer"].execute(state["context"])
    return {"context": ctx}


async def architecture_review(state: PipelineState) -> dict:
    """Run the full ArchitectReviewAgent sub-graph.

    The review agent stress-tests the architecture by:
    1. Challenging hidden assumptions
    2. Stress-testing trade-off decisions
    3. Auditing ADL coverage
    4. Computing governance score

    It also runs the style selection challenge (deterministic).
    """
    ctx = state["context"]

    # Run deterministic style selection challenge first
    ctx = _challenge_style_selection(ctx)

    # Run the full review agent if available
    if _review_agent is not None:
        ctx = await _review_agent.run(ctx)
    else:
        logger.warning("Review agent not initialized — skipping LLM review")

    return {"context": ctx}


def _challenge_style_selection(
    context: ArchitectureContext,
) -> ArchitectureContext:
    """Validate style selection against top characteristics and scenarios.

    Produces a style_selection_challenge entry in review_findings.
    This runs as part of the architecture_review node — it never
    mutates forward-pass fields, only review_findings.

    Args:
        context: The pipeline context after architecture generation.

    Returns:
        Context with review_findings["style_selection_challenge"] populated.
    """
    style_selection = context.architecture_design.get("style_selection", {})
    selected = style_selection.get("selected_style", "")
    style_scores = style_selection.get("style_scores", [])

    challenge: dict = {
        "challenged": False,
        "reason": "",
        "recommended_alternative": None,
    }

    if not selected or not style_scores:
        challenge["challenged"] = True
        challenge["reason"] = (
            "Style selection data is missing — cannot validate."
        )
        context.review_findings["style_selection_challenge"] = challenge
        return context

    # 1. Is the selected style consistent with the top 3 characteristics?
    top_characteristics = [
        c.get("name", "").lower()
        for c in context.characteristics[:3]
    ]
    selected_entry = next(
        (s for s in style_scores if s.get("style") == selected), None
    )
    if selected_entry and top_characteristics:
        driving = {
            d.lower()
            for d in selected_entry.get("driving_characteristics", [])
        }
        if top_characteristics[0] and top_characteristics[0] not in driving:
            challenge["challenged"] = True
            challenge["reason"] = (
                f"Top characteristic '{top_characteristics[0]}' is not "
                f"in the driving_characteristics of selected style "
                f"'{selected}'."
            )

    # 2. Check for improperly vetoed styles
    for score_entry in style_scores:
        if score_entry.get("vetoed") and not score_entry.get("veto_reason"):
            challenge["challenged"] = True
            challenge["reason"] += (
                f" Style '{score_entry.get('style')}' was vetoed "
                f"without a reason."
            )

    # 3. Would the large-scale scenario break the selected style?
    large_scenarios = [
        s for s in context.scenarios
        if s.get("tier", "").lower() == "large"
    ]
    if large_scenarios and selected.lower() in (
        "layered", "layered (n-tier)", "modular monolith",
        "microkernel", "pipeline",
    ):
        challenge["challenged"] = True
        large_desc = large_scenarios[0].get("description", "")
        challenge["reason"] += (
            f" Large-scale scenario ('{large_desc[:80]}') may exceed "
            f"the capacity of monolithic style '{selected}'."
        )
        # Suggest the runner-up as the alternative
        runner_up = style_selection.get("runner_up", "")
        if runner_up:
            challenge["recommended_alternative"] = runner_up

    challenge["reason"] = challenge["reason"].strip()
    context.review_findings["style_selection_challenge"] = challenge
    return context
