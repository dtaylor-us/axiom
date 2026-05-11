"""
Semantic gap reconciliation for the workshop agent.

Evaluates accumulated context against open gaps and updates their
resolution_confidence scores.

Runs after identify_gaps and before scenario/attribute elicitation so
question generation does not repeat topics already covered indirectly.

Design principle: gaps are uncertainty windows, not checklists.
"""

from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import InformationGap, WorkshopContext

logger = logging.getLogger(__name__)


class GapReconciler:
    """
    Updates gap resolution confidence against accumulated workshop context.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Args:
            llm_client: Shared LLM client for reconciliation prompts.
        """
        self._llm_client = llm_client

    async def reconcile(self, context: WorkshopContext) -> WorkshopContext:
        """
        Evaluate open gaps against accumulated evidence and update scores.

        Args:
            context: Workshop state with accumulated evidence.

        Returns:
            Context with updated gap confidences (monotonic non-decreasing).
        """
        open_gaps = [g for g in context.gaps if not g.filled]
        if not open_gaps:
            return context

        accumulated_evidence = self._build_evidence_digest(context)

        prompt = load_prompt(
            "workshop/reconcile_gaps",
            accumulated_evidence=accumulated_evidence,
            open_gaps=[g.model_dump(mode="json") for g in open_gaps],
        )

        raw = await self._llm_client.complete(
            prompt, response_format="json",
        )
        parsed = json.loads(raw)

        evaluations = {
            e["gap_id"]: e
            for e in parsed.get("gap_evaluations", [])
            if isinstance(e, dict) and e.get("gap_id")
        }

        updated_gaps: list[InformationGap] = []
        newly_resolved: list[str] = []

        for gap in context.gaps:
            if gap.gap_id not in evaluations:
                updated_gaps.append(gap)
                continue

            ev = evaluations[gap.gap_id]
            raw_conf = float(ev.get("resolution_confidence", 0))
            new_confidence = max(gap.resolution_confidence, raw_conf)
            new_evidence = ev.get("evidence_phrases", [])
            if not isinstance(new_evidence, list):
                new_evidence = []
            residual = str(ev.get("residual_question", "") or "")

            was_filled = gap.filled
            merged_evidence = list(dict.fromkeys(
                gap.resolution_evidence + [str(x) for x in new_evidence],
            ))

            updated_gap = gap.model_copy(update={
                "resolution_confidence": new_confidence,
                "resolution_evidence": merged_evidence,
                "residual_question": residual,
            })
            if updated_gap.filled and not was_filled:
                updated_gap = updated_gap.model_copy(update={
                    "filled_in_turn": context.current_turn,
                })
                newly_resolved.append(gap.gap_id)

            updated_gaps.append(updated_gap)

        if newly_resolved:
            logger.info(
                "Gap reconciliation resolved %d gaps. session=%s gaps=%s",
                len(newly_resolved),
                context.session_id,
                newly_resolved,
            )

        updated_open = [g.gap_id for g in updated_gaps if not g.filled]

        return context.model_copy(update={
            "gaps": updated_gaps,
            "open_gaps": updated_open,
        })

    def _build_evidence_digest(self, context: WorkshopContext) -> list[dict]:
        """
        Build structured evidence from user inputs and derived facts.

        Args:
            context: Full workshop context.

        Returns:
            List of evidence entries for the reconciliation prompt.
        """
        evidence: list[dict] = []
        for i, raw_input in enumerate(context.raw_inputs):
            evidence.append({
                "turn": i + 1,
                "type": "user_input",
                "content": raw_input[:2000],
            })
        for attr in context.attributes:
            for quote in attr.evidence_quotes:
                evidence.append({
                    "turn": attr.derived_in_turn,
                    "type": "evidence_quote",
                    "attribute": attr.name,
                    "content": quote,
                })
        for ws in context.scenarios:
            if ws.evidence_quote:
                evidence.append({
                    "turn": ws.derived_in_turn,
                    "type": "workshop_scenario",
                    "scenario_id": ws.scenario_id,
                    "content": ws.evidence_quote,
                })
        for gap in context.gaps:
            if gap.filled:
                evidence.append({
                    "turn": gap.filled_in_turn or 0,
                    "type": "gap_resolution",
                    "gap_id": gap.gap_id,
                    "content": f"{gap.description} — resolved",
                })
        return evidence
