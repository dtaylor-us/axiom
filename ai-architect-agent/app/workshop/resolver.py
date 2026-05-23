"""
Attribute question resolution engine for the workshop agent.

For each attribute with open questions, searches accumulated
workshop context for answers and applies them to the attribute.

This is the missing bridge between conversational answers and
structured artifacts. Without this component, open questions
accumulate indefinitely regardless of what the user says.

Runs after gap reconciliation and before new scenario/attribute
elicitation. This ordering ensures that existing artifacts are
updated before new ones are derived.

Design principle: prefer in-place update over re-derivation.
An existing attribute with evidence should be refined, not
replaced. Re-deriving from scratch discards accumulated
confidence and evidence_quotes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import (
    ElicitedAttribute,
    QAScenario,
    ResolvedAnswer,
    WorkshopContext,
)

logger = logging.getLogger(__name__)

_SCENARIO_FIELDS = (
    "stimulus",
    "source",
    "environment",
    "artifact",
    "response",
    "response_measure",
)


def _norm_question(q: str) -> str:
    return " ".join(q.split())


class AttributeQuestionResolver:
    """
    Resolves open questions on existing attributes by mapping
    conversational answers to the specific questions that
    generated them.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def resolve(
        self,
        context: WorkshopContext,
    ) -> WorkshopContext:
        """
        Resolves open questions across all attributes.

        For each attribute with open questions, calls the LLM
        to search accumulated context for answers. If found,
        updates the attribute in place: removes the resolved
        question, adds the answer as a structured fact, and
        updates the scenario if the answer contributes to a
        scenario field.

        Args:
            context: Workshop state with attributes and raw_inputs
        Returns:
            Updated context with attributes refined in place
        """
        attributes_with_questions = [
            a for a in context.attributes
            if a.open_questions
        ]

        if not attributes_with_questions:
            return context

        evidence = self._build_evidence(context)

        prompt = load_prompt(
            "workshop/resolve_questions",
            attributes_with_questions=[
                a.model_dump(mode="json") for a in attributes_with_questions
            ],
            accumulated_evidence=evidence,
            latest_input=context.raw_inputs[-1]
            if context.raw_inputs else "",
        )

        try:
            raw = await self._llm_client.complete(
                prompt, response_format="json"
            )
            parsed = json.loads(raw)
        except Exception:
            logger.warning(
                "resolve_questions LLM call failed — skipping. session=%s",
                context.session_id,
                exc_info=True,
            )
            return context

        resolutions_list = parsed.get("resolutions", [])
        if not isinstance(resolutions_list, list):
            resolutions_list = []

        resolutions: dict[str, dict[str, Any]] = {}
        for r in resolutions_list:
            if isinstance(r, dict) and r.get("attribute_id"):
                resolutions[str(r["attribute_id"])] = r

        updated_attributes: list[ElicitedAttribute] = []
        total_resolved = 0

        for attr in context.attributes:
            resolution = resolutions.get(attr.attribute_id)
            if not resolution:
                updated_attributes.append(attr)
                continue

            rq_raw = resolution.get("resolved_questions", [])
            if not isinstance(rq_raw, list):
                rq_raw = []
            resolved_norm = {_norm_question(str(q)) for q in rq_raw if q}

            remaining_questions = [
                q for q in attr.open_questions
                if _norm_question(q) not in resolved_norm
            ]

            new_evidence_raw = resolution.get("new_evidence_quotes", [])
            if not isinstance(new_evidence_raw, list):
                new_evidence_raw = []
            new_evidence = [str(x) for x in new_evidence_raw if x]

            scenario_updates = resolution.get("scenario_updates", {})
            if not isinstance(scenario_updates, dict):
                scenario_updates = {}

            confidence_upgrade = resolution.get("confidence_upgrade")
            if confidence_upgrade is not None:
                confidence_upgrade = str(confidence_upgrade).lower()
                if confidence_upgrade == "null":
                    confidence_upgrade = None

            updated_scenarios = list(attr.scenarios)
            scenario_was_updated = False
            if scenario_updates and updated_scenarios:
                primary = updated_scenarios[0]
                field_updates: dict[str, str] = {}
                for key in _SCENARIO_FIELDS:
                    v = scenario_updates.get(key)
                    if v and isinstance(v, str) and len(v.strip()) > 5:
                        field_updates[key] = v.strip()
                if field_updates:
                    merged_payload = {
                        **primary.model_dump(mode="python"),
                        **field_updates,
                    }
                    merged = QAScenario.model_validate(merged_payload)
                    updated_scenarios[0] = merged
                    scenario_was_updated = True

            resolved_count = len(attr.open_questions) - len(remaining_questions)
            total_resolved += resolved_count

            merged_quotes = list(dict.fromkeys(attr.evidence_quotes + new_evidence))

            new_conf = attr.confidence
            if (
                confidence_upgrade
                and confidence_upgrade in ("confirmed", "inferred", "tentative")
                and self._is_upgrade(attr.confidence, confidence_upgrade)
            ):
                new_conf = confidence_upgrade  # type: ignore[assignment]

            confidence_was_upgraded = new_conf != attr.confidence

            open_norms = {_norm_question(q) for q in attr.open_questions}
            new_resolved_entries = list(attr.resolved_answers)
            entries_raw = resolution.get("resolved_answer_entries", [])
            if isinstance(entries_raw, list) and entries_raw:
                for entry in entries_raw:
                    if not isinstance(entry, dict):
                        continue
                    qtext = str(entry.get("question", "") or "").strip()
                    if not qtext:
                        continue
                    qn = _norm_question(qtext)
                    if qn not in open_norms or qn not in resolved_norm:
                        continue
                    new_resolved_entries.append(
                        ResolvedAnswer(
                            question=qtext,
                            answer=str(entry.get("answer", "") or "").strip(),
                            resolved_in_turn=context.current_turn,
                            evidence_quote=str(
                                entry.get("evidence_quote", "") or ""
                            ).strip(),
                        )
                    )
            elif resolved_count > 0 and rq_raw:
                for qtext in rq_raw:
                    qn = _norm_question(str(qtext))
                    if qn not in open_norms or qn not in resolved_norm:
                        continue
                    new_resolved_entries.append(
                        ResolvedAnswer(
                            question=str(qtext),
                            answer="",
                            resolved_in_turn=context.current_turn,
                            evidence_quote=new_evidence[0]
                            if new_evidence
                            else "",
                        )
                    )

            # De-duplicate by question text (latest wins)
            by_q: dict[str, ResolvedAnswer] = {}
            for r in new_resolved_entries:
                by_q[r.question] = r
            deduped_resolved = list(by_q.values())

            count_increment = max(resolved_count, 0)
            new_q_count = attr.questions_resolved_count + count_increment

            summary_parts: list[str] = []
            if resolved_count > 0:
                summary_parts.append(
                    f"{resolved_count} question"
                    f"{'s' if resolved_count > 1 else ''} resolved"
                )
            if scenario_was_updated:
                updated_fields = [
                    k for k, v in scenario_updates.items()
                    if v and isinstance(v, str) and v.strip()
                ]
                if updated_fields:
                    summary_parts.append(
                        "scenario " + ", ".join(updated_fields) + " updated"
                    )
            if confidence_was_upgraded:
                summary_parts.append(
                    f"confidence upgraded to {new_conf}"
                )

            last_summary = attr.last_update_summary
            last_turn = attr.last_updated_turn
            if summary_parts:
                last_summary = "; ".join(summary_parts)
                last_turn = context.current_turn

            updated_attr = attr.model_copy(update={
                "open_questions": remaining_questions,
                "evidence_quotes": merged_quotes,
                "scenarios": updated_scenarios,
                "confidence": new_conf,
                "resolved_answers": deduped_resolved,
                "questions_resolved_count": new_q_count,
                "last_update_summary": last_summary,
                "last_updated_turn": last_turn,
            })
            updated_attributes.append(updated_attr)

            if resolved_count > 0:
                logger.info(
                    "Resolved %d questions on %s. remaining=%d session=%s",
                    resolved_count,
                    attr.name,
                    len(remaining_questions),
                    context.session_id,
                )

        if total_resolved > 0:
            logger.info(
                "Question resolution complete. session=%s total_resolved=%d",
                context.session_id,
                total_resolved,
            )

        return context.model_copy(update={
            "attributes": updated_attributes,
        })

    def _build_evidence(self, context: WorkshopContext) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for i, raw in enumerate(context.raw_inputs):
            evidence.append({
                "turn": i + 1,
                "type": "user_input",
                "content": raw[:3000],
            })
        for sc in context.scenarios:
            evidence.append({
                "turn": sc.derived_in_turn,
                "type": "scenario",
                "title": sc.title,
                "content": (
                    f"Stimulus: {sc.stimulus} "
                    f"Response: {sc.response} "
                    f"Measure: {sc.response_measure}"
                ),
            })
        return evidence

    @staticmethod
    def _is_upgrade(current: str, proposed: str) -> bool:
        order = ["confirmed", "inferred", "tentative"]
        try:
            return order.index(proposed) < order.index(current)
        except ValueError:
            return False
