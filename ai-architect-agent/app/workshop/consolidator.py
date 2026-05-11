"""
Quality attribute consolidation engine for the Quality Attribute Workshop.

ConsolidationEngine runs after every elicitation step and after every
user-triggered generation. Its job is to ensure the attribute list
stays bounded and semantically coherent:

  1. Normalise: map alias names to canonical categories via taxonomy.py
  2. Merge by taxonomy: combine attributes that share a canonical category
     when their scenario response measures are not distinctly different
  3. LLM deduplication: deeper semantic merge for remaining overlaps
  4. Separate non-QA: move non-measurable concerns to WorkshopContext.non_qa_concerns
  5. Cap: enforce MAX_ATTRIBUTES hard limit (ADL-037)

The engine is stateless — it takes a WorkshopContext and returns a new one.
It does NOT modify the attribute list in-place.

Boundary: does NOT import from app.pipeline or app.tools (ADL-001).
"""

from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import ElicitedAttribute, ResolvedAnswer, WorkshopContext
from app.workshop.taxonomy import (
    CANONICAL_ATTRIBUTES,
    is_non_qa_concern,
    normalise_attribute_name,
)

logger = logging.getLogger(__name__)

# Hard cap on the attribute list (ADL-037).
# If consolidation cannot reduce the list below this threshold,
# the lowest-importance attributes are trimmed rather than carried forward.
MAX_ATTRIBUTES: int = 12

# Merging a tiny attribute list collapses distinct architectural concerns.
MIN_ATTRIBUTES_FOR_CONSOLIDATION: int = 6

# Confidence rank for comparison helpers.
_CONFIDENCE_RANK: dict[str, int] = {"confirmed": 2, "inferred": 1, "tentative": 0}

# Importance rank for sorting / trimming.
_IMPORTANCE_RANK: dict[str, int] = {"critical": 3, "high": 2, "medium": 1, "low": 0}


class ConsolidationEngine:
    """
    Consolidates the quality attribute list in WorkshopContext.

    Designed for async use inside the LangGraph workshop graph.
    Construct once in QualityAttributeWorkshopAgent.__init__ and
    share the same instance across turns (it is stateless).

    Args:
        llm_client: The shared LLMClient for semantic deduplication.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def consolidate(self, context: WorkshopContext) -> WorkshopContext:
        """
        Run the five-step consolidation pipeline and return an updated context.

        Steps are applied in order; each step narrows the list further.
        The context is never mutated in-place — each step produces a new list.

        Args:
            context: WorkshopContext after the latest elicitation node.

        Returns:
            Updated WorkshopContext with a consolidated attribute list,
            updated non_qa_concerns, and last_consolidated_turn set.
        """
        if not context.attributes:
            return context

        if len(context.attributes) < MIN_ATTRIBUTES_FOR_CONSOLIDATION:
            return context

        attrs = list(context.attributes)

        # Step 1 — Normalise all alias names to canonical categories.
        attrs = self._normalise_all(attrs, context.current_turn)

        # Step 2 — Taxonomy-based merge for identical canonical categories.
        attrs = self._merge_by_taxonomy(attrs)

        # Step 3 — LLM semantic deduplication for remaining overlaps.
        attrs, non_qa_from_llm = await self._llm_deduplicate(attrs, context)

        # Step 4 — Separate remaining non-QA concerns.
        attrs, non_qa_from_taxonomy = self._separate_non_qa(attrs, context.current_turn)

        # Step 5 — Enforce MAX_ATTRIBUTES hard cap.
        attrs = self._cap_by_importance(attrs)

        # Merge all non-QA concerns found across steps.
        all_non_qa = list(context.non_qa_concerns) + non_qa_from_taxonomy + non_qa_from_llm

        logger.info(
            "Consolidation complete. session=%s before=%d after=%d non_qa=%d",
            context.session_id,
            len(context.attributes),
            len(attrs),
            len(non_qa_from_llm) + len(non_qa_from_taxonomy),
        )

        return context.model_copy(update={
            "attributes": attrs,
            "non_qa_concerns": all_non_qa,
            "last_consolidated_turn": context.current_turn,
        })

    # ------------------------------------------------------------------
    # Pipeline steps (private)
    # ------------------------------------------------------------------

    def _normalise_all(
        self,
        attrs: list[ElicitedAttribute],
        current_turn: int,
    ) -> list[ElicitedAttribute]:
        """
        Map every attribute's name through the taxonomy alias table.

        Updates canonical_name and classification fields. Does not merge;
        that happens in _merge_by_taxonomy.

        Args:
            attrs:        Current attribute list.
            current_turn: Turn number for provenance logging.

        Returns:
            List with canonical_name and classification populated.
        """
        normalised: list[ElicitedAttribute] = []
        for a in attrs:
            canonical_cat, _ = normalise_attribute_name(a.name)

            was_alias = (
                a.name.strip().lower() != canonical_cat
                and canonical_cat in CANONICAL_ATTRIBUTES
            )
            classification = (
                "alias" if was_alias
                else ("canonical" if canonical_cat in CANONICAL_ATTRIBUTES else "unknown")
            )

            normalised.append(a.model_copy(update={
                "canonical_name": canonical_cat,
                "classification": classification,
            }))
        return normalised

    def _merge_by_taxonomy(
        self,
        attrs: list[ElicitedAttribute],
    ) -> list[ElicitedAttribute]:
        """
        Merge attributes that share the same canonical_name.

        When two attributes map to the same canonical category, the one
        with higher confidence is kept as primary and the other's evidence
        is merged into it. Attributes are NOT merged when their scenario
        response measures are meaningfully different.

        Args:
            attrs: List after _normalise_all.

        Returns:
            Deduplicated list; merged attributes removed.
        """
        by_canonical: dict[str, list[ElicitedAttribute]] = {}
        for a in attrs:
            key = a.canonical_name or a.name.lower()
            by_canonical.setdefault(key, []).append(a)

        merged: list[ElicitedAttribute] = []
        for canonical_key, group in by_canonical.items():
            if len(group) == 1:
                merged.append(group[0])
                continue

            if self._has_distinct_scenarios(group):
                # Keep all — they represent distinct concerns despite sharing a category.
                merged.extend(group)
                continue

            # Highest confidence + importance first.
            primary = sorted(group, key=lambda a: (
                _CONFIDENCE_RANK.get(a.confidence, 0),
                _IMPORTANCE_RANK.get(a.importance, 0),
            ), reverse=True)[0]

            secondary_list = [a for a in group if a.attribute_id != primary.attribute_id]
            result = primary
            all_sub_concerns: list[str] = list(result.sub_concerns)

            for secondary in secondary_list:
                result = _merge_pair(result, secondary)
                all_sub_concerns.extend(secondary.sub_concerns)
                if secondary.name.lower() != result.name.lower():
                    all_sub_concerns.append(secondary.name)
                logger.info(
                    "Taxonomy merge: %s ← %s (category=%s)",
                    primary.attribute_id,
                    secondary.attribute_id,
                    canonical_key,
                )

            result = result.model_copy(update={
                "sub_concerns": list(dict.fromkeys(all_sub_concerns)),
                "classification": "canonical",
            })
            merged.append(result)

        return merged

    async def _llm_deduplicate(
        self,
        attrs: list[ElicitedAttribute],
        context: WorkshopContext,
    ) -> tuple[list[ElicitedAttribute], list[dict]]:
        """
        Ask the LLM to identify any remaining semantic duplicates.

        Only invoked when the list has ≥ 2 attributes. LLM failures are
        caught and logged; the unmodified list is returned so the pipeline
        continues even if the LLM is unavailable.

        Args:
            attrs:   Attribute list after taxonomy merge.
            context: WorkshopContext for system name and phase.

        Returns:
            Tuple of (updated_attr_list, non_qa_concerns_from_llm).
        """
        if len(attrs) < 2:
            return attrs, []

        attr_dicts = [
            {
                "attribute_id": a.attribute_id,
                "name": a.name,
                "canonical_name": a.canonical_name,
                "category": a.category,
                "description": a.description,
                "confidence": a.confidence,
                "importance": a.importance,
                "scenario_measures": [
                    sc.response_measure for sc in a.scenarios if sc.response_measure
                ],
            }
            for a in attrs
        ]

        prompt = load_prompt(
            "workshop/deduplicate_attributes",
            system_name=context.system_name,
            workshop_phase=context.workshop_phase,
            attributes=attr_dicts,
        )

        try:
            raw = await self._llm.complete(prompt, response_format="json")
            result = json.loads(raw)
        except Exception:
            logger.warning(
                "LLM deduplication failed — returning unmodified attribute list. "
                "session=%s",
                context.session_id,
                exc_info=True,
            )
            return attrs, []

        by_id: dict[str, ElicitedAttribute] = {a.attribute_id: a for a in attrs}
        absorbed_ids: set[str] = set()
        non_qa: list[dict] = []

        for group in result.get("merge_groups", []):
            primary_id = group.get("primary_attribute_id", "")
            absorbed = group.get("absorbed_attribute_ids", [])
            sub_concerns_from_llm = group.get("sub_concerns", [])

            if primary_id not in by_id:
                continue

            primary = by_id[primary_id]
            new_sub = list(primary.sub_concerns) + sub_concerns_from_llm

            for sec_id in absorbed:
                if sec_id not in by_id or sec_id == primary_id:
                    continue
                secondary = by_id[sec_id]
                primary = _merge_pair(primary, secondary)
                new_sub.extend(secondary.sub_concerns)
                absorbed_ids.add(sec_id)
                logger.info("LLM semantic merge: %s ← %s", primary_id, sec_id)

            by_id[primary_id] = primary.model_copy(update={
                "sub_concerns": list(dict.fromkeys(new_sub)),
            })

        for entry in result.get("non_qa_reclassifications", []):
            attr_id = entry.get("attribute_id", "")
            if attr_id in by_id:
                absorbed_ids.add(attr_id)
                non_qa.append({
                    "name": entry.get("name", ""),
                    "description": entry.get("description", ""),
                    "reason": entry.get("reason", ""),
                    "captured_in_turn": context.current_turn,
                })
                logger.info(
                    "LLM reclassified non-QA concern: %s (%s)",
                    entry.get("name"),
                    attr_id,
                )

        updated = [a for aid, a in by_id.items() if aid not in absorbed_ids]
        return updated, non_qa

    def _separate_non_qa(
        self,
        attrs: list[ElicitedAttribute],
        current_turn: int,
    ) -> tuple[list[ElicitedAttribute], list[dict]]:
        """
        Remove attributes whose names match the NON_QA_CONCEPTS taxonomy set.

        Any removed attribute is returned as a non_qa_concerns entry so the
        information is not lost — it is surfaced in the UI as a non-QA note.

        Args:
            attrs:        Attribute list after LLM deduplication.
            current_turn: Turn number for provenance.

        Returns:
            Tuple of (qa_attributes, non_qa_concerns).
        """
        qa: list[ElicitedAttribute] = []
        non_qa: list[dict] = []

        for a in attrs:
            if is_non_qa_concern(a.name):
                non_qa.append({
                    "name": a.name,
                    "description": a.description,
                    "reason": "taxonomy: not a measurable quality attribute",
                    "captured_in_turn": current_turn,
                })
                logger.info(
                    "Non-QA concern separated: %s (id=%s)", a.name, a.attribute_id
                )
            else:
                qa.append(a)

        return qa, non_qa

    def _cap_by_importance(
        self,
        attrs: list[ElicitedAttribute],
    ) -> list[ElicitedAttribute]:
        """
        Trim the attribute list to MAX_ATTRIBUTES, keeping the most important.

        Attributes are ranked by (importance rank DESC, confidence rank DESC).
        If the list is already within the cap, it is returned unchanged.

        Args:
            attrs: Attribute list after all merges.

        Returns:
            List with at most MAX_ATTRIBUTES entries.
        """
        if len(attrs) <= MAX_ATTRIBUTES:
            return attrs

        sorted_attrs = sorted(
            attrs,
            key=lambda a: (
                _IMPORTANCE_RANK.get(a.importance, 0),
                _CONFIDENCE_RANK.get(a.confidence, 0),
            ),
            reverse=True,
        )
        trimmed = sorted_attrs[:MAX_ATTRIBUTES]
        dropped = sorted_attrs[MAX_ATTRIBUTES:]

        logger.warning(
            "Attribute cap enforced (%d → %d). Dropped: %s",
            len(attrs),
            MAX_ATTRIBUTES,
            [a.name for a in dropped],
        )
        return trimmed

    @staticmethod
    def _has_distinct_scenarios(group: list[ElicitedAttribute]) -> bool:
        """
        Return True when two or more attributes in the group have measurably
        different response measures.

        Distinct means the response_measure strings share fewer than 30% of
        non-trivial tokens. When measures differ, the attributes represent
        different concerns even if they share a canonical category.

        Args:
            group: Candidate merge group (same canonical category).

        Returns:
            True if at least one pair has distinct scenario measures.
        """
        measures = [
            sc.response_measure.lower()
            for a in group
            for sc in a.scenarios
            if sc.response_measure and sc.response_measure.strip()
        ]
        if len(measures) < 2:
            return False

        stop_words = {"the", "a", "an", "of", "in", "to", "and", "or", "is", "are"}

        def tokens(s: str) -> set[str]:
            return {w for w in s.split() if w not in stop_words and len(w) > 2}

        for i, m1 in enumerate(measures):
            for m2 in measures[i + 1:]:
                t1, t2 = tokens(m1), tokens(m2)
                if not t1 or not t2:
                    continue
                overlap = t1 & t2
                smaller = min(len(t1), len(t2))
                if len(overlap) / smaller < 0.3:
                    return True
        return False


# ---------------------------------------------------------------------------
# Module-level helpers (shared with tests and the legacy sync path)
# ---------------------------------------------------------------------------

def _merge_pair(
    primary: ElicitedAttribute,
    secondary: ElicitedAttribute,
) -> ElicitedAttribute:
    """
    Merge secondary's evidence into primary, keeping primary's identity.

    The richer confidence and importance are retained. Evidence quotes and
    scenarios are union-merged. Open questions are combined.

    Args:
        primary:   Attribute to keep as the base.
        secondary: Attribute whose evidence is absorbed.

    Returns:
        Merged ElicitedAttribute with primary's attribute_id and name.
    """
    better_confidence = (
        primary.confidence
        if _CONFIDENCE_RANK.get(primary.confidence, 0)
           >= _CONFIDENCE_RANK.get(secondary.confidence, 0)
        else secondary.confidence
    )
    better_importance = (
        primary.importance
        if _IMPORTANCE_RANK.get(primary.importance, 0)
           >= _IMPORTANCE_RANK.get(secondary.importance, 0)
        else secondary.importance
    )

    merged_quotes = list(
        dict.fromkeys(primary.evidence_quotes + secondary.evidence_quotes)
    )

    existing_sc_ids = {sc.scenario_id for sc in primary.scenarios}
    merged_scenarios = list(primary.scenarios) + [
        sc for sc in secondary.scenarios
        if sc.scenario_id not in existing_sc_ids
    ]

    merged_questions = list(
        dict.fromkeys(primary.open_questions + secondary.open_questions)
    )

    merged_resolved_map: dict[str, ResolvedAnswer] = {}
    for r in primary.resolved_answers + secondary.resolved_answers:
        prev = merged_resolved_map.get(r.question)
        if prev is None or r.resolved_in_turn >= prev.resolved_in_turn:
            merged_resolved_map[r.question] = r
    merged_resolved = list(merged_resolved_map.values())
    merged_q_count = max(
        primary.questions_resolved_count,
        secondary.questions_resolved_count,
        len(merged_resolved),
    )

    last_turn = max(primary.last_updated_turn, secondary.last_updated_turn)
    last_summary = (
        primary.last_update_summary
        if primary.last_updated_turn >= secondary.last_updated_turn
        else secondary.last_update_summary
    )

    return primary.model_copy(update={
        "confidence":               better_confidence,
        "importance":               better_importance,
        "evidence_quotes":          merged_quotes,
        "scenarios":                merged_scenarios,
        "open_questions":           merged_questions,
        "resolved_answers":         merged_resolved,
        "questions_resolved_count": merged_q_count,
        "last_update_summary":      last_summary,
        "last_updated_turn":        last_turn,
    })


# ---------------------------------------------------------------------------
# Legacy helpers retained for backward compatibility with existing tests
# ---------------------------------------------------------------------------

def find_duplicates(
    attributes: list[ElicitedAttribute],
) -> list[tuple[str, str]]:
    """
    Identify pairs of attribute IDs that may be duplicates.

    Kept for backward compatibility with tests that were written
    against the original consolidator. New code should use
    ConsolidationEngine.consolidate() instead.
    """
    _OVERLAP_PAIRS: list[tuple[str, str]] = [
        ("availability",  "recoverability"),
        ("scalability",   "performance"),
        ("auditability",  "security"),
    ]
    duplicates: list[tuple[str, str]] = []
    for i, a in enumerate(attributes):
        for b in attributes[i + 1:]:
            if a.name.lower() == b.name.lower():
                duplicates.append((a.attribute_id, b.attribute_id))
                continue
            for cat1, cat2 in _OVERLAP_PAIRS:
                if sorted([a.category, b.category]) == sorted([cat1, cat2]):
                    duplicates.append((a.attribute_id, b.attribute_id))
    return duplicates


def merge_attributes(
    primary: ElicitedAttribute,
    secondary: ElicitedAttribute,
) -> ElicitedAttribute:
    """
    Merge two overlapping attributes, retaining the richer evidence.

    Kept for backward compatibility. New code should use
    ConsolidationEngine.consolidate() instead.
    """
    return _merge_pair(primary, secondary)


def completeness_score(attribute: ElicitedAttribute) -> float:
    """
    Compute a numeric completeness score for one attribute.

    Score is 0.0–1.0 based on scenario completeness and evidence density.
    """
    if not attribute.scenarios:
        return 0.0

    completeness_values = {
        "complete":      1.0,
        "partial":       0.7,
        "needs_measure": 0.4,
        "aspirational":  0.1,
    }

    best = max(
        completeness_values.get(sc.completeness, 0.0)
        for sc in attribute.scenarios
    )
    evidence_factor = min(len(attribute.evidence_quotes) / 3.0, 1.0)
    return best * (0.7 + 0.3 * evidence_factor)

