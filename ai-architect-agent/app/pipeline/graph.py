from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator, AsyncIterator

from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from app.models import ArchitectureContext
from app.observability import (
    pipeline_span, increment_active_runs, decrement_active_runs,
    record_stage_duration,
)
from app.llm.cost_tracker import start_tracking, get_tracker
from app.pipeline.formatter import format_response
from app.pipeline.nodes import (
    PipelineState,
    requirement_parsing,
    requirement_challenge,
    scenario_modeling,
    characteristic_inference,
    tactics_recommendation,
    conflict_analysis,
    architecture_generation,
    buy_vs_build_analysis,
    diagram_generation,
    trade_off_analysis,
    adl_generation,
    weakness_analysis,
    fmea_analysis,
    architecture_review,
)

logger = logging.getLogger(__name__)

# Heartbeat interval for keepalive comment lines.
# Keep at 15 seconds or less to avoid common proxy idle timeouts.
HEARTBEAT_INTERVAL_SECONDS = 15

# Ordered list of pipeline stages — determines execution order and edge topology
ORDERED_STAGES: list[str] = [
    "requirement_parsing",
    "requirement_challenge",
    "scenario_modeling",
    "characteristic_inference",
    "tactics_recommendation",   # stage 4b — after characteristics, before conflicts
    "conflict_analysis",
    "architecture_generation",
    "buy_vs_build_analysis",
    "diagram_generation",
    "trade_off_analysis",
    "adl_generation",
    "weakness_analysis",
    "fmea_analysis",
    "architecture_review",
]

_STAGE_SET: set[str] = set(ORDERED_STAGES)

_NODE_FN_MAP = {
    "requirement_parsing": requirement_parsing,
    "requirement_challenge": requirement_challenge,
    "scenario_modeling": scenario_modeling,
    "characteristic_inference": characteristic_inference,
    "tactics_recommendation": tactics_recommendation,
    "conflict_analysis": conflict_analysis,
    "architecture_generation": architecture_generation,
    "buy_vs_build_analysis": buy_vs_build_analysis,
    "diagram_generation": diagram_generation,
    "trade_off_analysis": trade_off_analysis,
    "adl_generation": adl_generation,
    "weakness_analysis": weakness_analysis,
    "fmea_analysis": fmea_analysis,
    "architecture_review": architecture_review,
}

# Compiled graph — set once via compile_pipeline()
_compiled = None


# -------------------------------------------------------------------
# NDJSON chunk helpers (mirrors agent.py's chunk format)
# -------------------------------------------------------------------

class _Chunk(BaseModel):
    type: str
    content: str | None = None
    stage: str | None = None
    toolName: str | None = None
    payload: dict | None = None
    conversationId: str | None = None
    metadata: dict | None = None


def _chunk(event_type: str, **kwargs: object) -> str:
    data = _Chunk(type=event_type, **kwargs)
    return data.model_dump_json(exclude_none=True) + "\n"


# -------------------------------------------------------------------
# Graph construction
# -------------------------------------------------------------------

def compile_pipeline() -> None:
    """Build the LangGraph StateGraph and compile it (called once at startup)."""
    global _compiled

    builder = StateGraph(PipelineState)

    for name, fn in _NODE_FN_MAP.items():
        builder.add_node(name, fn)

    builder.set_entry_point(ORDERED_STAGES[0])

    for i in range(len(ORDERED_STAGES) - 1):
        builder.add_edge(ORDERED_STAGES[i], ORDERED_STAGES[i + 1])

    builder.add_edge(ORDERED_STAGES[-1], END)

    _compiled = builder.compile()
    logger.info("Pipeline graph compiled with %d stages", len(ORDERED_STAGES))


# -------------------------------------------------------------------
# Streaming execution
# -------------------------------------------------------------------

async def run_pipeline(
    context: ArchitectureContext,
    memory_store: object | None = None,
) -> AsyncGenerator[str, None]:
    """Execute the full pipeline and yield NDJSON chunks as stages progress.

    Yields:
        NDJSON strings — one per line — following the STAGE_START / STAGE_COMPLETE /
        COMPLETE event protocol defined in ARCHITECTURE.md.
    """
    if _compiled is None:
        raise RuntimeError("Pipeline graph not compiled — call compile_pipeline() first")

    async def _pipeline_chunks() -> AsyncIterator[str]:
        """Yield NDJSON chunks produced by the compiled LangGraph."""
        nonlocal context
        initial_state: PipelineState = {"context": context}

        # Emit STAGE_START for the first stage before graph execution begins
        yield _chunk("STAGE_START", stage=ORDERED_STAGES[0])

        # Track per-stage wall-clock time for metrics
        stage_start_time: float = time.monotonic()

        # Start cost tracking for this pipeline run
        usage_tracker = start_tracking()

        increment_active_runs()
        try:
            async for event in _compiled.astream(initial_state, stream_mode="updates"):
                # event is dict[str, dict] — keys are node names, values are state updates
                for node_name, update in event.items():
                    if node_name not in _STAGE_SET:
                        continue

                    # Record stage duration from the last STAGE_START to now
                    elapsed = time.monotonic() - stage_start_time
                    record_stage_duration(node_name, elapsed)

                    # Update context from node output
                    if "context" in update:
                        context = update["context"]

                    # Build enriched payload for STAGE_COMPLETE
                    stage_payload: dict = _stage_payload(node_name, context)

                    yield _chunk(
                        "STAGE_COMPLETE",
                        stage=node_name,
                        payload=stage_payload,
                    )

                    # Emit STAGE_START for the next stage if there is one
                    idx = ORDERED_STAGES.index(node_name)
                    if idx + 1 < len(ORDERED_STAGES):
                        yield _chunk("STAGE_START", stage=ORDERED_STAGES[idx + 1])
                        stage_start_time = time.monotonic()
        except Exception as exc:
            logger.error("Pipeline error: %s", str(exc))
            yield _chunk(
                "ERROR",
                content=f"Pipeline error: {str(exc)}",
                payload={"error": str(exc), "conversationId": context.conversation_id},
            )
            return
        finally:
            decrement_active_runs()

        # ── Re-iteration gate ─────────────────────────────────────────
        if context.should_reiterate and not context.is_final_iteration:
            logger.info(
                "Re-iteration triggered (iteration=%d, score=%s)",
                context.iteration,
                context.governance_score,
            )
            yield _chunk(
                "RE_ITERATE",
                conversationId=context.conversation_id,
                payload={
                    "iteration": context.iteration,
                    "governance_score": context.governance_score,
                    "constraints": context.review_constraints,
                    "message": "Governance score below threshold — re-iterating pipeline.",
                },
            )

            # Increment iteration and re-run the pipeline
            context.iteration += 1
            async for re_chunk in run_pipeline(context, memory_store=memory_store):
                yield re_chunk
            return

        # Emit the formatted architecture report as CHUNK content
        report = format_response(context)
        yield _chunk("CHUNK", content=report)

        # Build structured output for persistence
        structured = {
            k: v for k, v in {
                "parsed_entities": context.parsed_entities,
                "missing_requirements": context.missing_requirements,
                "ambiguities": context.ambiguities,
                "hidden_assumptions": context.hidden_assumptions,
                "clarifying_questions": context.clarifying_questions,
                "scenarios": context.scenarios,
                "characteristics": context.characteristics,
                "tactics": context.tactics,
                "tactics_summary": context.tactics_summary,
                "characteristic_conflicts": context.characteristic_conflicts,
                "underrepresented_characteristics": context.underrepresented_characteristics,
                "overspecified_characteristics": context.overspecified_characteristics,
                "tension_summary": context.tension_summary,
                "architecture_design": context.architecture_design,
                "similar_past_designs": context.similar_past_designs,
                "buy_vs_build_analysis": context.buy_vs_build_analysis,
                "buy_vs_build_summary": context.buy_vs_build_summary,
                "mermaid_component_diagram": context.mermaid_component_diagram,
                "mermaid_sequence_diagram": context.mermaid_sequence_diagram,
                "diagrams": [d.model_dump() for d in context.diagrams],
                "trade_offs": context.trade_offs,
                "trade_off_dominant_tension": context.trade_off_dominant_tension,
                "adl_blocks_generated": len(context.adl_blocks),
                "adl_rules": [b.model_dump() for b in context.adl_blocks],
                "adl_document": context.adl_document,
                "weaknesses": context.weaknesses,
                "weakness_summary": context.weakness_summary,
                "fmea_risks": context.fmea_risks,
                "fmea_critical_risks": context.fmea_critical_risks,
                "review_findings": context.review_findings,
                "governance_score": context.governance_score,
                "governance_score_confidence": context.governance_score_confidence,
                "review_completed_fully": context.review_completed_fully,
                "failed_review_nodes": context.failed_review_nodes,
                "governance_score_breakdown": context.governance_score_breakdown,
                "improvement_recommendations": context.improvement_recommendations,
            }.items()
            if v  # only include non-empty fields
        }

        # Attach cost tracking data to context before building COMPLETE payload
        final_tracker = get_tracker()
        if final_tracker is not None:
            context.token_usage = final_tracker.to_dict()

        yield _chunk(
            "COMPLETE",
            conversationId=context.conversation_id,
            payload={
                "message": "Pipeline completed.",
                "stages_executed": len(ORDERED_STAGES),
                "iteration": context.iteration,
                "structured_output": structured,
                "token_usage": context.token_usage,
                "tactics_recommended": len(context.tactics),
                "tactics_already_addressed": sum(
                    1 for t in context.tactics if t.get("already_addressed")
                ),
            },
        )

        # Fire-and-forget: store design in Qdrant for future similarity lookups
        if memory_store and context.architecture_design:
            asyncio.create_task(_store_design_safe(
                memory_store, context,
            ))

    async def _heartbeat(queue: asyncio.Queue[str | None]) -> None:
        """Emit keepalive comment lines while the pipeline is running."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
                await queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            return

    heartbeat_queue: asyncio.Queue[str | None] = asyncio.Queue()
    heartbeat_task = asyncio.create_task(_heartbeat(heartbeat_queue))

    pipeline_iter = _pipeline_chunks().__aiter__()
    next_pipeline_task: asyncio.Task[str] | None = None
    try:
        while True:
            if next_pipeline_task is None:
                next_pipeline_task = asyncio.create_task(pipeline_iter.__anext__())

            next_heartbeat_task = asyncio.create_task(heartbeat_queue.get())
            done, pending = await asyncio.wait(
                {next_pipeline_task, next_heartbeat_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if next_pipeline_task in done:
                next_heartbeat_task.cancel()
                try:
                    await next_heartbeat_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                yield next_pipeline_task.result()
                next_pipeline_task = None
                continue

            if next_heartbeat_task in done:
                comment = next_heartbeat_task.result()
                if comment is not None:
                    yield comment
                continue
    except StopAsyncIteration:
        return
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


def _stage_payload(stage: str, context: ArchitectureContext) -> dict:
    """Build a standardized STAGE_COMPLETE payload for a stage."""
    payload: dict = {"status": "complete", "stage": stage}

    if stage == "characteristic_inference":
        payload["characteristic_count"] = len(context.characteristics)
    elif stage == "tactics_recommendation":
        payload["tactic_count"] = len(context.tactics)
        payload["characteristics_covered"] = list({
            t.get("characteristic_name")
            for t in context.tactics
            if t.get("characteristic_name")
        })
        payload["already_addressed_count"] = sum(
            1 for t in context.tactics if t.get("already_addressed")
        )
        payload["new_tactics_count"] = sum(
            1 for t in context.tactics if not t.get("already_addressed")
        )
        payload["critical_count"] = sum(
            1 for t in context.tactics if t.get("priority") == "critical"
        )
        payload["tactics_summary"] = context.tactics_summary
    elif stage == "conflict_analysis":
        payload["conflict_count"] = len(context.characteristic_conflicts)
    elif stage == "architecture_generation":
        payload["style"] = context.selected_architecture_style
        payload["style_scores"] = [
            {
                "style": s.get("style"),
                "score": s.get("score"),
                "vetoed": s.get("vetoed"),
            }
            for s in context.architecture_design.get(
                "style_selection", {}
            ).get("style_scores", [])
        ]
        payload["runner_up"] = context.architecture_design.get(
            "style_selection", {}
        ).get("runner_up")
        payload["component_count"] = len(context.architecture_design.get("components", []))
        payload["interaction_count"] = len(context.architecture_design.get("interactions", []))
        payload["override_applied"] = context.architecture_design.get("override_applied", False)
        payload["override_type"] = context.architecture_override.get("type", "none")
        payload["override_warning"] = context.architecture_design.get("override_warning", "")
    elif stage == "buy_vs_build_analysis":
        payload["decision_count"] = len(context.buy_vs_build_analysis)
        payload["build_count"] = sum(
            1 for d in context.buy_vs_build_analysis if d.get("recommendation") == "build"
        )
        payload["buy_count"] = sum(
            1 for d in context.buy_vs_build_analysis if d.get("recommendation") == "buy"
        )
        payload["adopt_count"] = sum(
            1 for d in context.buy_vs_build_analysis if d.get("recommendation") == "adopt"
        )
        payload["conflict_count"] = sum(
            1 for d in context.buy_vs_build_analysis if d.get("conflicts_with_user_preference")
        )
        payload["summary"] = context.buy_vs_build_summary
    elif stage == "diagram_generation":
        payload["diagram_count"] = len(context.diagrams)
        payload["diagram_types"] = [d.type.value for d in context.diagrams]
        payload["diagrams"] = [
            {
                "diagram_id": d.diagram_id,
                "type": d.type.value,
                "title": d.title,
                "description": d.description,
                "source_lines": len([line for line in d.mermaid_source.split("\n") if line.strip()]),
            }
            for d in context.diagrams
        ]
    elif stage == "trade_off_analysis":
        payload["decision_count"] = len(context.trade_offs)
        payload["dominant_tension"] = context.trade_off_dominant_tension
    elif stage == "adl_generation":
        payload["block_count"] = len(context.adl_blocks)
        payload["hard_count"] = sum(1 for b in context.adl_blocks if b.enforcement_level == "hard")
        payload["soft_count"] = sum(1 for b in context.adl_blocks if b.enforcement_level == "soft")
        payload["characteristics_covered"] = list({
            b.characteristic_enforced for b in context.adl_blocks if b.characteristic_enforced
        })
    elif stage == "fmea_analysis":
        payload.update({
            "execution_order": "sequential",
            "weakness_count": len(context.weaknesses),
            "fmea_count": len(context.fmea_risks),
            "critical_fmea_count": len(context.fmea_critical_risks),
            "most_critical_fmea": context.fmea_critical_risks[0]
            if context.fmea_critical_risks else None,
            "weakness_summary": context.weakness_summary,
            "fmea_used_weakness_context": len(context.weaknesses) > 0,
        })
    elif stage == "architecture_review":
        payload["governance_score"] = context.governance_score
        payload["governance_score_confidence"] = context.governance_score_confidence
        payload["review_completed_fully"] = context.review_completed_fully
        payload["failed_review_nodes"] = context.failed_review_nodes
        payload["governance_score_breakdown"] = context.governance_score_breakdown
        payload["should_reiterate"] = context.should_reiterate
        payload["critical_findings"] = len([
            a for a in context.review_findings.get("assumption_challenges", [])
            if a.get("severity") == "critical"
        ])
        payload["recommendation_count"] = len(context.improvement_recommendations)

    return payload


async def _store_design_safe(
    memory_store: object, context: ArchitectureContext,
) -> None:
    """Best-effort background store — never raises."""
    try:
        await memory_store.store_design(  # type: ignore[attr-defined]
            conversation_id=context.conversation_id,
            requirements=context.raw_requirements,
            architecture_design=context.architecture_design,
            characteristics=context.characteristics,
        )
    except Exception:
        logger.warning("Failed to store design after pipeline", exc_info=True)
