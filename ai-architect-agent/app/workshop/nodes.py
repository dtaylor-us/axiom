"""
Workshop conversation graph nodes.

Each node processes one step in the quality attribute elicitation
conversation. Nodes follow the same structural contract as the
main pipeline nodes: receive state, call LLM via prompts, return
updated state.

The critical ordering invariant (ADL-037 / ADL-038):
  identify_gaps MUST execute before scenario elicitation on every turn.

This enforces the ask-before-assert principle — the agent must
know what is missing before it can claim to know what is present.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig

from app.llm.client import LLMClient
from app.prompts.loader import load_prompt
from app.workshop.context import (
    ElicitedAttribute,
    InformationGap,
    QAScenario,
    WorkshopContext,
    WorkshopScenario,
    WorkshopTurn,
)

logger = logging.getLogger(__name__)

# Phase transition map: given enough evidence in a phase, advance to the next.
# The agent evaluates transition readiness in check_phase_transition_node.
_PHASE_ORDER = [
    "input_analysis",
    "business_context",
    "usage_context",
    "technical_context",
    "risk_priority",
    "scenario_brainstorm",
    "scenario_refinement",
    "attribute_consolidation",
    "validation",
    "complete",
]

# Phases in which the agent may derive quality attributes.
# Before risk_priority, critical gaps almost certainly remain open.
_ELICITATION_ELIGIBLE_PHASES = {
    "risk_priority",
    "scenario_brainstorm",
    "scenario_refinement",
    "attribute_consolidation",
    "validation",
}

# Number of critical gaps that must be filled before attribute
# confidence can reach "inferred" or "confirmed".
# While even one critical gap is open, confidence is capped at "tentative".
_CRITICAL_GAP_THRESHOLD = 0

# Maximum prior turns included in the question-generation prompt (token budget).
_RECENT_TURNS_WINDOW = 5

# Consolidation merges aggressively when the list is tiny — wait for breadth first.
MIN_ATTRIBUTES_FOR_CONSOLIDATION = 6

_CATEGORY_VALUES = frozenset({
    "availability", "performance", "security", "modifiability",
    "scalability", "testability", "deployability", "usability",
    "interoperability", "data_integrity", "auditability",
    "recoverability", "cost", "other",
})

_GAP_CATEGORY_TO_FACT_CATEGORY = {
    "business_context": "business",
    "usage_context": "usage",
    "technical_context": "technical",
    "risk_priority": "risk",
}

_ATTR_CATEGORY_TO_FACT_CATEGORY = {
    "availability": "technical",
    "performance": "usage",
    "security": "risk",
    "modifiability": "technical",
    "scalability": "usage",
    "testability": "technical",
    "deployability": "technical",
    "usability": "usage",
    "interoperability": "technical",
    "data_integrity": "technical",
    "auditability": "risk",
    "recoverability": "technical",
    "cost": "business",
    "other": "technical",
}


def _build_session_summary(state: WorkshopContext) -> str:
    """Short prose summary of workshop progress for facilitator prompts."""
    return (
        f"System: {state.system_name or 'not yet identified'}. "
        f"Gaps: {state.filled_gaps}/{state.total_gaps} filled. "
        f"Attributes: {len(state.attributes)} identified."
    )


def _extract_known_facts(state: WorkshopContext) -> list[dict[str, str]]:
    """
    Facts established before the current user message.

    Used so analyse_input and gap identification do not re-extract
    information already captured in prior turns or filled gaps.

    Args:
        state: Current workshop context (latest user message already in raw_inputs).

    Returns:
        List of dicts with keys ``category`` and ``fact`` for prompt rendering.
    """
    facts: list[dict[str, str]] = []
    if state.system_name:
        facts.append({
            "category": "business",
            "fact": f"System name: {state.system_name}",
        })
    for g in state.gaps:
        if g.filled:
            cat = _GAP_CATEGORY_TO_FACT_CATEGORY.get(g.category, "business")
            facts.append({"category": cat, "fact": g.description})
    for t in state.turns:
        preview = (t.user_input or "").strip()
        if preview:
            facts.append({
                "category": "business",
                "fact": f"(Turn {t.turn_number}) {preview[:500]}",
            })
    for a in state.attributes:
        fc = _ATTR_CATEGORY_TO_FACT_CATEGORY.get(a.category, "technical")
        if a.description.strip():
            facts.append({"category": fc, "fact": a.description})
    return facts


def _questions_overlap(q1: str, q2: str) -> bool:
    """
    Simple overlap check using keyword intersection ratio.

    Args:
        q1: First string (typically normalised lower-case).
        q2: Second string.

    Returns:
        True when the two strings share enough non-stop-word tokens.
    """
    stop_words = {
        "what", "are", "the", "for", "and", "how", "who",
        "is", "a", "an", "of", "in", "to", "your", "this",
    }
    words1 = {w for w in q1.split() if w not in stop_words}
    words2 = {w for w in q2.split() if w not in stop_words}
    if not words1 or not words2:
        return False
    overlap = words1 & words2
    smaller = min(len(words1), len(words2))
    return len(overlap) / smaller > 0.5


def _filter_already_answered_questions(
    questions: list[dict],
    filled_gaps: list[InformationGap],
    state: WorkshopContext,
) -> list[dict]:
    """
    Remove questions that repeat filled-gap topics or recent agent questions.

    Defence-in-depth when the facilitator LLM ignores conversation history.

    Args:
        questions: Structured question dicts from the LLM (``question`` key).
        filled_gaps: Gaps already marked filled in this session.
        state: Workshop context (for recent ``questions_asked``).

    Returns:
        Filtered question list.
    """
    filled_descriptions = {g.description.lower() for g in filled_gaps}
    recent_questions = {
        q.lower()
        for turn in state.turns[-3:]
        for q in turn.questions_asked
    }

    filtered: list[dict] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        question_text = (q.get("question") or "").lower()
        is_redundant = any(
            _questions_overlap(question_text, filled_desc)
            for filled_desc in filled_descriptions
        )
        is_repeat = any(
            _questions_overlap(question_text, prior)
            for prior in recent_questions
        )
        if is_redundant or is_repeat:
            logger.warning(
                "Removing redundant question. session=%s question=%s reason=%s",
                state.session_id,
                question_text[:100],
                "filled_gap" if is_redundant else "repeat",
            )
        else:
            filtered.append(q)

    return filtered


def _get_llm(config: RunnableConfig) -> LLMClient:
    """
    Extract the LLM client from the LangGraph RunnableConfig.

    Args:
        config: LangGraph RunnableConfig; custom values are in config['configurable'].

    Returns:
        The LLMClient instance.

    Raises:
        RuntimeError: If the LLMClient is not in config.
    """
    client = (config.get("configurable") or {}).get("llm_client")
    if client is None:
        raise RuntimeError(
            "LLMClient not found in graph config. "
            "Pass it via config={'configurable': {'llm_client': ...}} in ainvoke()."
        )
    return client


def _open_critical_gaps(ctx: WorkshopContext) -> list[InformationGap]:
    """Return all open gaps with critical priority."""
    return [
        g for g in ctx.gaps
        if not g.filled and g.priority == "critical"
    ]


def _normalize_attr_category(value: object) -> str:
    """Normalise LLM category strings to ElicitedAttribute literals."""
    s = (str(value) if value is not None else "").strip().lower()
    return s if s in _CATEGORY_VALUES else "other"


def _scenario_payload_to_qa(raw: dict) -> QAScenario:
    """Build a ``QAScenario`` from LLM JSON; completeness is recomputed post-init."""
    return QAScenario(
        scenario_id=raw.get("scenario_id") or f"SC-{uuid.uuid4().hex[:6].upper()}",
        stimulus=str(raw.get("stimulus", "") or ""),
        source=str(raw.get("source", "") or ""),
        environment=str(raw.get("environment", "") or ""),
        artifact=str(raw.get("artifact", "") or ""),
        response=str(raw.get("response", "") or ""),
        response_measure=str(raw.get("response_measure", "") or ""),
        completeness="aspirational",
    )


async def analyze_input_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Node 1 — analyse the latest user input for extractable facts.

    Calls the analyze_input prompt. Extracts system name, business
    facts, usage signals, technical constraints, and implicit quality
    concerns. Does NOT derive quality attributes — that comes later.

    Args:
        state:  Current WorkshopContext.
        config: LangGraph config with 'llm_client' and 'latest_input'.

    Returns:
        Updated WorkshopContext with system_name set if discovered.
    """
    llm: LLMClient = _get_llm(config)
    latest_input: str = (config.get("configurable") or {}).get("latest_input", "")

    prior_known_facts = _extract_known_facts(state)

    prompt = load_prompt(
        "workshop/analyze_input",
        raw_input=latest_input,
        system_name=state.system_name,
        workshop_phase=state.workshop_phase,
        prior_input_count=len(state.turns),
        prior_known_facts=prior_known_facts,
    )

    try:
        raw = await llm.complete(prompt, response_format="json")
        analysis = json.loads(raw)
    except Exception:
        logger.warning(
            "analyze_input_node LLM call failed — continuing with empty analysis. "
            "session=%s turn=%d",
            state.session_id,
            state.current_turn,
            exc_info=True,
        )
        analysis = {"system_name": "", "extracted_facts": []}

    # Promote the system name if the LLM discovered it and we don't have one.
    if analysis.get("system_name") and not state.system_name:
        state = state.model_copy(update={"system_name": analysis["system_name"]})

    logger.debug(
        "analyze_input_node complete. session=%s facts=%d",
        state.session_id,
        len(analysis.get("extracted_facts", [])),
    )
    return state


async def identify_gaps_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Node 2 — identify missing information before deriving attributes.

    This is the heart of the ask-before-assert principle. The node
    inspects what is known and what is not, and produces a prioritised
    list of information gaps. Critical gaps block attribute derivation.

    Must execute before scenario elicitation on every turn.

    Args:
        state:  Current WorkshopContext.
        config: LangGraph config with 'llm_client' and 'latest_input'.

    Returns:
        Updated WorkshopContext with new gaps added and existing gaps
        marked as filled based on the latest user input.
    """
    llm: LLMClient = _get_llm(config)
    latest_input: str = (config.get("configurable") or {}).get("latest_input", "")

    known_facts = {
        "system_name": state.system_name,
        "raw_input_count": len(state.raw_inputs),
        "existing_attributes": [
            {"name": a.name, "confidence": a.confidence}
            for a in state.attributes
        ],
        "latest_input_preview": latest_input[:500],
    }

    prompt = load_prompt(
        "workshop/identify_gaps",
        known_facts=known_facts,
        existing_gaps=[g.model_dump() for g in state.gaps],
    )

    try:
        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)
    except Exception:
        logger.warning(
            "identify_gaps_node LLM call failed — skipping gap update. "
            "session=%s turn=%d",
            state.session_id,
            state.current_turn,
            exc_info=True,
        )
        parsed = {"new_gaps": [], "gaps_filled_by_latest_input": []}

    filled_ids = set(parsed.get("gaps_filled_by_latest_input", []))

    updated_gaps: list[InformationGap] = []
    for gap in state.gaps:
        if gap.gap_id in filled_ids:
            was_filled = gap.filled
            new_rc = max(gap.resolution_confidence, 0.92)
            extra_evidence: list[str] = []
            if latest_input.strip():
                extra_evidence.append(latest_input.strip()[:500])
            merged_evidence = list(dict.fromkeys(
                gap.resolution_evidence + extra_evidence,
            ))
            upd: dict = {
                "resolution_confidence": new_rc,
                "resolution_evidence": merged_evidence,
            }
            probe = gap.model_copy(update=upd)
            if probe.filled and not was_filled:
                upd["filled_in_turn"] = state.current_turn
            updated_gaps.append(gap.model_copy(update=upd))
        else:
            updated_gaps.append(gap)

    existing_ids = {g.gap_id for g in state.gaps}
    new_gap_models: list[InformationGap] = []
    for raw_gap in parsed.get("new_gaps", []):
        gap_id = raw_gap.get("gap_id", f"GAP-{uuid.uuid4().hex[:6].upper()}")
        if gap_id in existing_ids:
            continue
        try:
            gap = InformationGap(
                gap_id=gap_id,
                category=raw_gap["category"],
                description=raw_gap["description"],
                questions=raw_gap.get("questions", []),
                priority=raw_gap.get("priority", "medium"),
            )
            new_gap_models.append(gap)
            existing_ids.add(gap_id)
        except Exception:
            logger.warning(
                "Malformed gap from LLM — skipping. gap_id=%s", gap_id
            )

    all_gaps = updated_gaps + new_gap_models

    open_gap_ids = [g.gap_id for g in all_gaps if not g.filled]

    logger.info(
        "Gap update complete. session=%s turn=%d total=%d filled=%d open=%d "
        "newly_filled=%s",
        state.session_id,
        state.current_turn,
        len(all_gaps),
        sum(1 for g in all_gaps if g.filled),
        len(open_gap_ids),
        list(filled_ids),
    )

    return state.model_copy(update={
        "gaps": all_gaps,
        "open_gaps": open_gap_ids,
    })


async def reconcile_gaps_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Reconcile open gaps against accumulated evidence (semantic pass).

    Runs after identify_gaps so indirect answers lift confidence before
    questions are generated.

    Args:
        state: Current workshop context.
        config: LangGraph config with optional ``reconciler``.

    Returns:
        Updated context with monotonic gap confidence scores.
    """
    reconciler = (config.get("configurable") or {}).get("reconciler")
    if reconciler is None or not state.gaps:
        return state
    return await reconciler.reconcile(state)


async def resolve_attribute_questions_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Resolves open questions on existing attributes from
    accumulated evidence.

    Runs BEFORE elicit_scenarios so that scenario extraction
    builds on up-to-date attribute state.

    This node is responsible for the answer-to-artifact binding
    that makes the workshop a feedback loop rather than a
    one-way questionnaire.
    """
    resolver = (config.get("configurable") or {}).get("resolver")
    if resolver is None:
        return state

    attributes_with_questions = [
        a for a in state.attributes if a.open_questions
    ]
    if not attributes_with_questions:
        return state

    return await resolver.resolve(state)


async def elicit_scenarios_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Primary elicitation step — derive concrete operational scenarios.

    Args:
        state: Workshop context after gap reconciliation.
        config: LangGraph config with ``llm_client`` and ``latest_input``.

    Returns:
        Context with ``scenarios`` merged by ``scenario_id``.
    """
    if state.workshop_phase not in _ELICITATION_ELIGIBLE_PHASES:
        logger.debug(
            "elicit_scenarios_node: phase=%s not eligible — skipping. session=%s",
            state.workshop_phase,
            state.session_id,
        )
        return state

    llm: LLMClient = _get_llm(config)
    latest_input: str = (config.get("configurable") or {}).get("latest_input", "")

    known_facts = _extract_known_facts(state)
    evidence_digest: list[dict[str, object]] = []
    for i, raw in enumerate(state.raw_inputs):
        evidence_digest.append({
            "turn": i + 1,
            "content": raw[:2000],
        })

    existing_snapshot = [s.model_dump(mode="json") for s in state.scenarios]
    existing_ids = {s.scenario_id for s in state.scenarios}

    prompt = load_prompt(
        "workshop/elicit_scenarios",
        known_facts=known_facts,
        all_evidence=evidence_digest,
        latest_input=latest_input,
        existing_scenarios=existing_snapshot,
        existing_scenario_ids=sorted(existing_ids),
    )

    try:
        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)
    except Exception:
        logger.warning(
            "elicit_scenarios_node LLM call failed — skipping. session=%s",
            state.session_id,
            exc_info=True,
        )
        return state

    by_id: dict[str, WorkshopScenario] = {s.scenario_id: s for s in state.scenarios}
    for raw_sc in parsed.get("scenarios", []):
        if not isinstance(raw_sc, dict):
            continue
        sid = raw_sc.get("scenario_id") or f"SC-{uuid.uuid4().hex[:6].upper()}"
        if sid in by_id:
            continue
        try:
            ws = WorkshopScenario(
                scenario_id=sid,
                title=str(raw_sc.get("title", "") or ""),
                stimulus=str(raw_sc.get("stimulus", "") or ""),
                source=str(raw_sc.get("source", "") or ""),
                environment=str(raw_sc.get("environment", "") or ""),
                artifact=str(raw_sc.get("artifact", "") or ""),
                response=str(raw_sc.get("response", "") or ""),
                response_measure=str(raw_sc.get("response_measure", "") or ""),
                exercises_attributes=list(raw_sc.get("exercises_attributes") or []),
                evidence_quote=str(raw_sc.get("evidence_quote", "") or ""),
                derived_in_turn=state.current_turn,
            )
            by_id[ws.scenario_id] = ws
        except Exception:
            logger.warning("Malformed workshop scenario from LLM — skipping")

    merged = list(by_id.values())
    out = state.model_copy(update={"scenarios": merged}).refresh_scenario_counts()
    logger.debug(
        "elicit_scenarios_node complete. session=%s scenarios=%d",
        out.session_id,
        len(merged),
    )
    return out


async def infer_attributes_from_scenarios_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Infer ``ElicitedAttribute`` rows from accumulated ``WorkshopScenario`` artifacts.

    Args:
        state: Context containing workshop scenarios.
        config: LangGraph config with ``llm_client``.

    Returns:
        Context with attributes merged and confidence upgrades applied.
    """
    if state.workshop_phase not in _ELICITATION_ELIGIBLE_PHASES:
        return state

    critical_open = _open_critical_gaps(state)
    if len(critical_open) > _CRITICAL_GAP_THRESHOLD:
        logger.debug(
            "infer_attributes_from_scenarios_node: critical gaps open — skipping. "
            "session=%s",
            state.session_id,
        )
        return state

    if not state.scenarios:
        return state

    llm: LLMClient = _get_llm(config)

    existing_attributes = [
        {
            "attribute_id": a.attribute_id,
            "name": a.name,
            "confidence": a.confidence,
        }
        for a in state.attributes
    ]

    prompt = load_prompt(
        "workshop/infer_attributes_from_scenarios",
        scenarios=[s.model_dump(mode="json") for s in state.scenarios],
        existing_attributes=existing_attributes,
    )

    try:
        raw = await llm.complete(prompt, response_format="json")
        parsed = json.loads(raw)
    except Exception:
        logger.warning(
            "infer_attributes_from_scenarios_node LLM call failed — skipping. "
            "session=%s",
            state.session_id,
            exc_info=True,
        )
        return state

    new_attributes = list(state.attributes)
    existing_ids = {a.attribute_id for a in new_attributes}
    id_index = {a.attribute_id: i for i, a in enumerate(new_attributes)}

    for raw_attr in parsed.get("new_attributes", []):
        if not isinstance(raw_attr, dict):
            continue
        attr_id = raw_attr.get("attribute_id", f"QA-{uuid.uuid4().hex[:6].upper()}")
        if attr_id in existing_ids:
            continue

        scen_raw = raw_attr.get("scenario")
        scenarios: list[QAScenario] = []
        if isinstance(scen_raw, dict):
            try:
                scenarios.append(_scenario_payload_to_qa(scen_raw))
            except Exception:
                logger.warning("Malformed primary scenario for attribute %s", attr_id)

        confidence = str(raw_attr.get("confidence", "tentative")).lower()
        if confidence not in ("confirmed", "inferred", "tentative"):
            confidence = "tentative"
        if _open_critical_gaps(state) and confidence != "tentative":
            confidence = "tentative"

        try:
            attr = ElicitedAttribute(
                attribute_id=attr_id,
                name=str(raw_attr.get("name", "Unknown")),
                category=_normalize_attr_category(raw_attr.get("category")),
                description=str(raw_attr.get("description", "")),
                importance=str(raw_attr.get("importance", "medium")),
                confidence=confidence,
                evidence_quotes=list(raw_attr.get("evidence_quotes") or []),
                scenarios=scenarios,
                open_questions=list(raw_attr.get("open_questions") or []),
                derived_in_turn=state.current_turn,
            )
            new_attributes.append(attr)
            existing_ids.add(attr_id)
            id_index[attr_id] = len(new_attributes) - 1
        except Exception:
            logger.warning("Malformed attribute %s from LLM — skipping", attr_id)

    for upgrade in parsed.get("confidence_upgrades", []):
        if not isinstance(upgrade, dict):
            continue
        aid = upgrade.get("attribute_id")
        if not aid or aid not in id_index:
            continue
        new_conf = str(upgrade.get("new_confidence", "")).lower()
        if new_conf not in ("confirmed", "inferred", "tentative"):
            continue
        if _open_critical_gaps(state) and new_conf != "tentative":
            new_conf = "tentative"
        idx = id_index[aid]
        cur = new_attributes[idx]
        upgrade_parts = [
            f"confidence upgraded to {new_conf}",
        ]
        new_attributes[idx] = cur.model_copy(update={
            "confidence": new_conf,
            "last_update_summary": "; ".join(upgrade_parts),
            "last_updated_turn": state.current_turn,
        })

    out = state.model_copy(update={"attributes": new_attributes})
    logger.debug(
        "infer_attributes_from_scenarios_node complete. session=%s attrs=%d",
        out.session_id,
        len(new_attributes),
    )
    return out


async def consolidation_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Merge and deduplicate attributes once the list is large enough to justify it.

    Args:
        state: Workshop context after inference.
        config: LangGraph config with optional ``consolidator``.

    Returns:
        Possibly consolidated context.
    """
    if len(state.attributes) < MIN_ATTRIBUTES_FOR_CONSOLIDATION:
        return state
    if state.last_consolidated_turn == state.current_turn:
        return state
    consolidator = (config.get("configurable") or {}).get("consolidator")
    if consolidator is None:
        logger.debug(
            "consolidation_node: no consolidator — skipping. session=%s",
            state.session_id,
        )
        return state
    return await consolidator.consolidate(state)


async def check_phase_transition_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Node 4 — evaluate whether the session should advance to the next phase.

    Phase transition criteria (evidence-based, not turn-count-based):

      input_analysis    → business_context:    always, after first turn
      business_context  → usage_context:       all business_context gaps filled
      usage_context     → technical_context:   all usage_context gaps filled
      technical_context → risk_priority:       all technical_context gaps filled
      risk_priority     → scenario_brainstorm: zero critical open gaps,
                                               OR (≥3 strong attrs AND ≤2 critical
                                               open AND current_turn ≥ 4)
      scenario_brainstorm → scenario_refinement: ≥3 grounded workshop scenarios
      scenario_refinement → attribute_consolidation: ≥5 grounded workshop scenarios
      attribute_consolidation → validation:    one full turn has completed in this phase
      validation        → complete:            signalled by generate_response LLM output

    Args:
        state:  Current WorkshopContext.
        config: LangGraph config (unused here).

    Returns:
        Updated WorkshopContext, possibly with an advanced phase.
    """
    current_idx = _PHASE_ORDER.index(state.workshop_phase)

    if state.workshop_phase == "complete":
        return state

    if state.workshop_phase == "input_analysis":
        # Always move past input_analysis after the first turn — we have data.
        next_phase = _PHASE_ORDER[current_idx + 1]
        return state.model_copy(update={"workshop_phase": next_phase})

    # Context-gathering phases: transition when that category's gaps are clear.
    category_phase_map = {
        "business_context":  "business_context",
        "usage_context":     "usage_context",
        "technical_context": "technical_context",
    }

    if state.workshop_phase in category_phase_map:
        category = category_phase_map[state.workshop_phase]
        open_in_category = [
            g for g in state.gaps
            if g.category == category and not g.filled
        ]
        if not open_in_category:
            next_phase = _PHASE_ORDER[current_idx + 1]
            logger.info(
                "Phase transition %s → %s. session=%s",
                state.workshop_phase,
                next_phase,
                state.session_id,
            )
            return state.model_copy(update={"workshop_phase": next_phase})
        return state

    if state.workshop_phase == "risk_priority":
        critical_open = _open_critical_gaps(state)
        strong_attrs = sum(
            1 for a in state.attributes
            if a.confidence in ("inferred", "confirmed")
        )
        no_critical = len(critical_open) == 0
        sufficient_with_gaps = (
            strong_attrs >= 3
            and len(critical_open) <= 2
            and state.current_turn >= 4
        )
        if no_critical or sufficient_with_gaps:
            next_phase = _PHASE_ORDER[current_idx + 1]
            logger.info(
                "Phase transition risk_priority → %s. session=%s "
                "critical_open=%d strong_attrs=%d turns=%d",
                next_phase,
                state.session_id,
                len(critical_open),
                strong_attrs,
                state.current_turn,
            )
            return state.model_copy(update={"workshop_phase": next_phase})
        return state

    if state.workshop_phase == "scenario_brainstorm":
        grounded = sum(
            1 for s in state.scenarios
            if s.completeness != "aspirational"
        )
        if grounded >= 3:
            next_phase = _PHASE_ORDER[current_idx + 1]
            logger.info(
                "Phase transition scenario_brainstorm → %s. session=%s "
                "grounded_scenarios=%d",
                next_phase,
                state.session_id,
                grounded,
            )
            return state.model_copy(update={"workshop_phase": next_phase})
        return state

    if state.workshop_phase == "scenario_refinement":
        grounded = sum(
            1 for s in state.scenarios
            if s.completeness != "aspirational"
        )
        if grounded >= 5:
            next_phase = _PHASE_ORDER[current_idx + 1]
            logger.info(
                "Phase transition scenario_refinement → %s. session=%s "
                "grounded_scenarios=%d",
                next_phase,
                state.session_id,
                grounded,
            )
            return state.model_copy(update={"workshop_phase": next_phase})
        return state

    # attribute_consolidation and validation advance only via LLM signal.
    return state


async def generate_response_node(
    state: WorkshopContext,
    config: RunnableConfig,
) -> WorkshopContext:
    """
    Node 5 — generate the agent's conversational response for this turn.

    Calls the generate_questions prompt to produce an acknowledgement of
    what the user said, a progress note, and 1-3 targeted questions
    for the highest priority open gaps.

    Records the completed turn in state.turns (append-only).

    Args:
        state:  Current WorkshopContext after all upstream nodes.
        config: LangGraph config with 'llm_client' and 'latest_input'.

    Returns:
        Updated WorkshopContext with the new turn appended.
    """
    llm: LLMClient = _get_llm(config)
    latest_input: str = (config.get("configurable") or {}).get("latest_input", "")

    recent_turns = (
        state.turns[-_RECENT_TURNS_WINDOW:] if state.turns else []
    )
    filled_gaps_list = [g for g in state.gaps if g.filled]

    open_gaps_summary = []
    for g in state.gaps:
        if g.filled:
            continue
        primary = (g.residual_question.strip() if g.residual_question.strip()
                   else (g.questions[0] if g.questions else ""))
        open_gaps_summary.append({
            "gap_id": g.gap_id,
            "category": g.category,
            "description": g.description,
            "priority": g.priority,
            "questions": g.questions[:2],
            "residual_question": g.residual_question,
            "primary_question": primary,
            "resolution_confidence": g.resolution_confidence,
        })

    tentative_attributes = [
        {
            "attribute_id": a.attribute_id,
            "name": a.name,
            "confidence": a.confidence,
            "open_questions": a.open_questions,
        }
        for a in state.attributes
        if a.confidence == "tentative"
    ]

    prompt = load_prompt(
        "workshop/generate_questions",
        workshop_phase=state.workshop_phase,
        session_summary=_build_session_summary(state),
        recent_turns=[t.model_dump() for t in recent_turns],
        filled_gaps=[g.model_dump() for g in filled_gaps_list],
        open_gaps=open_gaps_summary,
        tentative_attributes=tentative_attributes,
        last_user_input=latest_input,
    )

    try:
        raw = await llm.complete(prompt, response_format="json")
        response_data = json.loads(raw)
    except Exception:
        logger.error(
            "generate_response_node LLM call failed. session=%s turn=%d",
            state.session_id,
            state.current_turn,
            exc_info=True,
        )
        raise

    acknowledgement = response_data.get("acknowledgement", "")
    progress_note = response_data.get("progress_note", "")
    raw_questions = response_data.get("questions", [])
    question_dicts = [q for q in raw_questions if isinstance(q, dict)]
    questions = _filter_already_answered_questions(
        question_dicts,
        filled_gaps_list,
        state,
    )

    # Build the agent's prose response from the structured parts
    agent_message_parts: list[str] = []
    if acknowledgement:
        agent_message_parts.append(acknowledgement)
    if progress_note:
        agent_message_parts.append(progress_note)
    for i, q in enumerate(questions, start=1):
        q_text = q.get("question", "") if isinstance(q, dict) else str(q)
        agent_message_parts.append(f"{i}. {q_text}")

    agent_message = "\n\n".join(agent_message_parts)
    questions_asked = [
        (q.get("question", "") if isinstance(q, dict) else str(q))
        for q in questions
    ]

    # Handle phase transition signalled by the LLM
    phase_transition = response_data.get("phase_transition", "")
    updated_phase = state.workshop_phase
    if (
        phase_transition
        and phase_transition != state.workshop_phase
        and phase_transition in _PHASE_ORDER
    ):
        updated_phase = phase_transition
        logger.info(
            "LLM-signalled phase transition %s → %s. session=%s",
            state.workshop_phase,
            updated_phase,
            state.session_id,
        )

    # Identify gap_ids addressed this turn (any gap that got marked filled
    # between the start of this turn and now)
    gaps_filled_this_turn = [
        g.gap_id for g in state.gaps
        if g.filled and g.filled_in_turn == state.current_turn
    ]

    attrs_this_turn = [
        a.attribute_id for a in state.attributes
        if a.derived_in_turn == state.current_turn
    ]

    new_turn = WorkshopTurn(
        turn_number=state.current_turn,
        user_input=latest_input,
        agent_response=agent_message,
        gaps_identified=gaps_filled_this_turn,
        attributes_derived=attrs_this_turn,
        questions_asked=questions_asked,
        workshop_phase=updated_phase,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )

    updated_turns = list(state.turns) + [new_turn]
    is_now_complete = updated_phase == "complete"

    state = state.model_copy(update={
        "turns": updated_turns,
        "workshop_phase": updated_phase,
        "is_complete": is_now_complete,
        "last_updated": datetime.now(tz=timezone.utc).isoformat(),
    })

    logger.info(
        "generate_response_node complete. session=%s turn=%d phase=%s "
        "questions=%d",
        state.session_id,
        state.current_turn,
        state.workshop_phase,
        len(questions_asked),
    )
    return state
