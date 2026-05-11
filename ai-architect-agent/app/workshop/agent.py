"""
Quality Attribute Workshop agent.

A conversational LangGraph agent that facilitates structured
quality attribute elicitation following the SEI QAW method
(CMU/SEI-2001-TR-020) and Bass, Clements, Kazman "Software
Architecture in Practice" 4th ed.

This agent is separate from the main architecture pipeline.
It shares the LLM client and prompt loader infrastructure
but has its own graph, its own context model, and its own
persistence path through Spring Boot.

The agent is stateless across requests — the WorkshopContext
is passed in with every turn and returned updated. Persistence
is handled by Spring Boot via the workshop session endpoints.

Conversation flow:
  Turn N: user provides input
  Agent:  1. Analyse the input for facts and implicit concerns
          2. Identify new gaps or mark existing gaps as filled
          3. Update tentative quality attributes if evidence supports
          4. Generate targeted questions for the highest priority gaps
          5. Return structured response with updated context

The agent does not derive final attributes until gaps in the
critical category are filled. It does not assert attributes
without evidence.
"""

import json
import logging
from typing import Any

from langgraph.graph import StateGraph, END
from app.workshop.context import (
    WorkshopContext,
    ElicitedAttribute,
    QAScenario,
)
from app.workshop.consolidator import ConsolidationEngine
from app.workshop.gap_reconciler import GapReconciler
from app.workshop.resolver import AttributeQuestionResolver
from app.workshop.nodes import (
    analyze_input_node,
    identify_gaps_node,
    reconcile_gaps_node,
    resolve_attribute_questions_node,
    elicit_scenarios_node,
    infer_attributes_from_scenarios_node,
    consolidation_node,
    generate_response_node,
    check_phase_transition_node,
    _extract_known_facts,
)
from app.llm.client import LLMClient
from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

_CATEGORY_VALUES = frozenset({
    "availability", "performance", "security", "modifiability",
    "scalability", "testability", "deployability", "usability",
    "interoperability", "data_integrity", "auditability",
    "recoverability", "cost", "other",
})


def _summarise_inputs(raw_inputs: list[str], max_chars: int = 4000) -> str:
    joined = "\n\n---\n\n".join(raw_inputs)
    if len(joined) <= max_chars:
        return joined
    return joined[:max_chars] + "\n…"


def _normalize_category(value: object) -> str:
    s = (str(value) if value is not None else "").strip().lower()
    return s if s in _CATEGORY_VALUES else "other"


def _normalize_importance(value: object) -> str:
    s = (str(value) if value is not None else "medium").strip().lower()
    return s if s in ("critical", "high", "medium", "low") else "medium"


def _normalize_confidence(value: object) -> str:
    s = (str(value) if value is not None else "tentative").strip().lower()
    return s if s in ("confirmed", "inferred", "tentative") else "tentative"


def _normalize_completeness(value: object) -> str:
    s = (str(value) if value is not None else "aspirational").strip().lower()
    ok = ("complete", "partial", "needs_measure", "aspirational")
    return s if s in ok else "aspirational"


def _build_elicited_attribute_from_generation(
    attr_data: dict[str, Any],
    *,
    derived_in_turn: int,
    generation_pass: int,
    existing: ElicitedAttribute | None,
) -> ElicitedAttribute:
    aid = str(attr_data.get("attribute_id") or "").strip()
    if not aid and existing:
        aid = existing.attribute_id
    if not aid:
        aid = "QA-UNKNOWN"

    scen_raw = attr_data.get("scenario") if isinstance(
        attr_data.get("scenario"), dict
    ) else {}
    scenario = QAScenario(
        scenario_id=f"{aid}-primary",
        stimulus=str(scen_raw.get("stimulus") or ""),
        source=str(scen_raw.get("source") or ""),
        environment=str(scen_raw.get("environment") or ""),
        artifact=str(scen_raw.get("artifact") or ""),
        response=str(scen_raw.get("response") or ""),
        response_measure=str(
            scen_raw.get("response_measure")
            or scen_raw.get("responseMeasure")
            or ""
        ),
        completeness="aspirational",
    )

    quotes = attr_data.get("evidence_quotes") or []
    if not isinstance(quotes, list):
        quotes = []
    quotes = [str(q) for q in quotes if q is not None]

    oq = attr_data.get("open_questions") or []
    if not isinstance(oq, list):
        oq = []
    oq = [str(q) for q in oq if q is not None]

    wiw = attr_data.get("would_improve_with") or []
    if not isinstance(wiw, list):
        wiw = []
    wiw = [str(x) for x in wiw if x is not None]

    raw_name = attr_data.get("name")
    if raw_name is not None and str(raw_name).strip():
        name = str(raw_name).strip()
    elif existing:
        name = existing.name
    else:
        name = "Unknown"

    desc = str(attr_data.get("description") or "").strip()
    if not desc and existing:
        desc = existing.description

    first_gp = (
        existing.first_generation_pass
        if existing and existing.first_generation_pass is not None
        else generation_pass
    )

    return ElicitedAttribute(
        attribute_id=aid,
        name=name,
        category=_normalize_category(attr_data.get("category")),
        description=desc,
        importance=_normalize_importance(attr_data.get("importance")),
        confidence=_normalize_confidence(attr_data.get("confidence")),
        evidence_quotes=quotes,
        scenarios=[scenario],
        open_questions=oq,
        resolved_answers=list(existing.resolved_answers) if existing else [],
        questions_resolved_count=(
            existing.questions_resolved_count if existing else 0
        ),
        last_update_summary=existing.last_update_summary if existing else "",
        last_updated_turn=existing.last_updated_turn if existing else 0,
        derived_in_turn=derived_in_turn,
        first_generation_pass=first_gp,
        last_generation_pass=generation_pass,
        would_improve_with=wiw,
    )


class QualityAttributeWorkshopAgent:
    """
    Conversational agent for quality attribute elicitation.

    Each call to process_turn() runs one full conversation turn:
    input analysis, gap identification, attribute elicitation,
    and response generation. The updated WorkshopContext is
    returned and must be persisted by the caller.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        Initialise the agent with a shared LLM client.

        Args:
            llm_client: Shared LLMClient instance from app.state.
        """
        self._llm_client = llm_client
        self._consolidator = ConsolidationEngine(llm_client)
        self._reconciler = GapReconciler(llm_client)
        self._resolver = AttributeQuestionResolver(llm_client)
        self._graph = self._build_graph()

    def _build_graph(self) -> object:
        """
        Build the LangGraph conversation graph.

        Node ordering is intentional and enforced by ADL-038 / scenario-first QAW:
          analyze_input → identify_gaps → reconcile_gaps → resolve_questions →
          elicit_scenarios → infer_attributes_from_scenarios → consolidation →
          check_transition → generate_response → END

        identify_gaps MUST precede scenario elicitation so the agent cannot
        treat speculation as evidence.
        """
        graph = StateGraph(WorkshopContext)

        graph.add_node("analyze_input", analyze_input_node)
        graph.add_node("identify_gaps", identify_gaps_node)
        graph.add_node("reconcile_gaps", reconcile_gaps_node)
        graph.add_node("resolve_questions", resolve_attribute_questions_node)
        graph.add_node("elicit_scenarios", elicit_scenarios_node)
        graph.add_node(
            "infer_attributes_from_scenarios",
            infer_attributes_from_scenarios_node,
        )
        graph.add_node("consolidation", consolidation_node)
        graph.add_node("check_transition", check_phase_transition_node)
        graph.add_node("generate_response", generate_response_node)

        graph.set_entry_point("analyze_input")
        graph.add_edge("analyze_input", "identify_gaps")
        graph.add_edge("identify_gaps", "reconcile_gaps")
        graph.add_edge("reconcile_gaps", "resolve_questions")
        graph.add_edge("resolve_questions", "elicit_scenarios")
        graph.add_edge("elicit_scenarios", "infer_attributes_from_scenarios")
        graph.add_edge("infer_attributes_from_scenarios", "consolidation")
        graph.add_edge("consolidation", "check_transition")
        graph.add_edge("check_transition", "generate_response")
        graph.add_edge("generate_response", END)

        return graph.compile()

    async def process_turn(
        self,
        context: WorkshopContext,
        user_input: str,
    ) -> tuple[WorkshopContext, dict]:
        """
        Process one conversation turn.

        Appends the user input to context, increments the turn counter,
        runs the full graph, and returns the updated context plus a
        structured turn response for the UI.

        Args:
            context:    Current workshop session state.
            user_input: The user's latest message or input document.

        Returns:
            Tuple of (updated_context, turn_response).
            turn_response contains the agent's message, questions,
            current gaps, and current attributes for the UI.
        """
        prior_generation_count = context.generation_count
        updates: dict[str, Any] = {
            "raw_inputs": list(context.raw_inputs) + [user_input],
            "current_turn": context.current_turn + 1,
        }
        if prior_generation_count > 0:
            updates["attributes_stale"] = True
        state_in = context.model_copy(update=updates)

        config = {
            "configurable": {
                "llm_client":   self._llm_client,
                "latest_input": user_input,
                "consolidator": self._consolidator,
                "reconciler":   self._reconciler,
                "resolver":     self._resolver,
            },
        }

        updated_context = await self._graph.ainvoke(state_in, config=config)

        # LangGraph returns a dict when the state is a Pydantic model;
        # reconstruct the model from the dict if needed.
        if isinstance(updated_context, dict):
            updated_context = WorkshopContext.model_validate(updated_context)

        if prior_generation_count > 0:
            updated_context = updated_context.model_copy(update={
                "attributes_stale": True,
            })

        turn_response = self._build_turn_response(updated_context)

        logger.info(
            "Workshop turn complete. session=%s turn=%d phase=%s "
            "gaps_open=%d attributes=%d",
            state_in.session_id,
            updated_context.current_turn,
            updated_context.workshop_phase,
            len(updated_context.open_gaps),
            len(updated_context.attributes),
        )

        return updated_context, turn_response

    async def assess_generation_readiness(
        self,
        context: WorkshopContext,
    ) -> dict[str, Any]:
        """
        Produces an honest assessment of what the current evidence
        will support if the user generates attributes now.

        Called when the user hovers over or clicks the generate
        button — gives them the information to make an informed
        decision before committing.

        Does not modify context. Read-only assessment.
        """
        # Keep readiness prompts small and stable — workshop contexts can grow large
        # and otherwise hit provider limits.
        known_facts = _extract_known_facts(context)[:60]
        filled_gaps = [g for g in context.gaps if g.filled][:30]
        open_gaps = [g for g in context.gaps if not g.filled][:30]
        input_summary = _summarise_inputs(context.raw_inputs, max_chars=1500)
        tentative_attrs = context.attributes[:20]

        prompt = load_prompt(
            "workshop/assess_generation_readiness",
            known_facts=known_facts,
            filled_gaps=[g.model_dump() for g in filled_gaps],
            open_gaps=[g.model_dump() for g in open_gaps],
            turn_count=len(context.turns),
            input_summary=input_summary,
            tentative_attributes=[a.model_dump() for a in tentative_attrs],
        )

        raw = await self._llm_client.complete(
            prompt, response_format="json"
        )
        assessment = json.loads(raw)

        logger.info(
            "Generation readiness assessed. session=%s "
            "readiness=%s can_produce=%s",
            context.session_id,
            assessment.get("overall_readiness"),
            assessment.get("can_produce_useful_output"),
        )

        return assessment

    async def generate_from_current_evidence(
        self,
        context: WorkshopContext,
    ) -> tuple[WorkshopContext, dict[str, Any]]:
        """
        Generates quality attributes from whatever evidence exists.

        Called when the user explicitly requests generation.
        Always generates — never refuses based on gap count.
        Confidence levels on the output reflect evidence quality.

        The session remains open after generation. The user can
        continue providing context and regenerate at any time.
        Attributes are updated, not replaced, on regeneration.

        Returns:
            Updated context with attributes populated or updated,
            and a generation response dict for the UI.
        """
        if not context.can_generate:
            raise ValueError(
                "Cannot generate: no input has been provided yet. "
                "Submit at least one turn of context first."
            )

        assessment = await self.assess_generation_readiness(context)

        known_facts = _extract_known_facts(context)[:80]
        filled_gaps = [g for g in context.gaps if g.filled][:40]
        system_context = context.system_name or "unknown system"

        prompt = load_prompt(
            "workshop/generate_from_evidence",
            known_facts=known_facts,
            filled_gaps=[g.model_dump() for g in filled_gaps],
            turn_count=len(context.turns),
            system_context=system_context,
            readiness_assessment=assessment,
            existing_attributes=[
                a.model_dump() for a in context.attributes[:30]
            ],
        )

        raw = await self._llm_client.complete(
            prompt, response_format="json"
        )
        parsed = json.loads(raw)

        existing_by_name = {
            a.name.lower(): a for a in context.attributes
        }
        updated_attributes = list(context.attributes)

        pass_num = context.generation_count + 1

        for attr_data in parsed.get("attributes", []):
            if not isinstance(attr_data, dict):
                continue
            name_key = (attr_data.get("name") or "").strip().lower()
            existing = existing_by_name.get(name_key) if name_key else None
            elicited = _build_elicited_attribute_from_generation(
                attr_data,
                derived_in_turn=context.current_turn,
                generation_pass=pass_num,
                existing=existing,
            )
            if name_key and name_key in existing_by_name:
                idx = next(
                    i for i, a in enumerate(updated_attributes)
                    if a.name.lower() == name_key
                )
                updated_attributes[idx] = elicited
            else:
                updated_attributes.append(elicited)
                if name_key:
                    existing_by_name[name_key] = elicited

        updated_context = context.model_copy(update={
            "attributes": updated_attributes,
            "generation_requested": True,
            "generation_count": pass_num,
            "last_generation_turn": context.current_turn,
            "attributes_stale": False,
            "pre_generation_assessment": assessment,
        })

        # Consolidate immediately after generation so the attribute list is
        # bounded and semantically coherent before the response is built.
        updated_context = await self._consolidator.consolidate(updated_context)

        generation_response = {
            "session_id":            context.session_id,
            "generation_count":      updated_context.generation_count,
            "overall_readiness":     assessment.get("overall_readiness", ""),
            "confidence_note":       assessment.get("confidence_note", ""),
            "attributes_generated":  len(updated_attributes),
            "attribute_preview":     assessment.get("attribute_preview", []),
            "high_value_gaps":       assessment.get("high_value_gaps", []),
            "missing_domains":       assessment.get("missing_domains", []),
            "generation_summary":    parsed.get("generation_summary", ""),
            "attributes":            [
                {
                    "attribute_id":    a.attribute_id,
                    "name":            a.name,
                    "importance":      a.importance,
                    "confidence":      a.confidence,
                    "description":     a.description,
                    "scenario_completeness": (
                        a.scenarios[0].completeness
                        if a.scenarios else "aspirational"
                    ),
                    "open_questions":  a.open_questions,
                }
                for a in updated_attributes
            ],
            "can_continue_refining": True,
            "continuation_prompt":
                "You can continue providing context to refine "
                "these attributes. Each new turn will update "
                "the attributes as your evidence grows.",
            "attributes_stale":       updated_context.attributes_stale,
        }

        logger.info(
            "Attributes generated from evidence. session=%s "
            "count=%d readiness=%s generation_number=%d",
            context.session_id,
            len(updated_attributes),
            assessment.get("overall_readiness"),
            updated_context.generation_count,
        )

        return updated_context, generation_response

    def _build_turn_response(self, ctx: WorkshopContext) -> dict:
        """
        Build the structured response dict sent to Spring Boot.

        Spring Boot forwards this to the UI via the REST response.
        The shape matches WorkshopTurnResponseDto on the Java side.

        Args:
            ctx: Updated WorkshopContext after the turn.

        Returns:
            Dict containing the agent message, gap summary, attributes,
            and pipeline-readiness signal.
        """
        latest_turn = ctx.turns[-1] if ctx.turns else None
        return {
            "session_id":         ctx.session_id,
            "turn_number":        ctx.current_turn,
            "workshop_phase":     ctx.workshop_phase,
            "agent_message":      latest_turn.agent_response if latest_turn else "",
            "questions_asked":    latest_turn.questions_asked if latest_turn else [],
            "gap_summary": {
                "total":               ctx.total_gaps,
                "filled":              ctx.filled_gaps,
                "completion_pct":      ctx.gap_completion_pct,
                "in_progress_count":   ctx.progress_snapshot.in_progress_count,
                "open_gaps": [
                    {
                        "gap_id":                g.gap_id,
                        "category":              g.category,
                        "description":           g.description,
                        "priority":              g.priority,
                        "residual_question":     g.residual_question,
                        "resolution_confidence": g.resolution_confidence,
                    }
                    for g in ctx.gaps
                    if not g.filled
                ],
            },
            "attributes": [
                {
                    "attribute_id":         a.attribute_id,
                    "name":                 a.name,
                    "importance":           a.importance,
                    "confidence":           a.confidence,
                    "description":          a.description,
                    "scenario_completeness": (
                        a.scenarios[0].completeness
                        if a.scenarios else "aspirational"
                    ),
                    "open_questions":       a.open_questions,
                }
                for a in ctx.attributes
            ],
            "is_complete":              ctx.is_complete,
            "has_sufficient_attributes": ctx.has_sufficient_attributes,
            "ready_for_pipeline":       (
                ctx.is_complete and ctx.has_sufficient_attributes
            ),
        }

    async def produce_summary(self, context: WorkshopContext) -> dict:
        """
        Produce the final QA summary when the workshop is complete.

        The summary is structured for direct input into the main
        Archon architecture pipeline. It is distinct from the
        turn-by-turn response — it is a comprehensive, one-time
        synthesis of everything elicited during the session.

        Args:
            context: Completed WorkshopContext.

        Returns:
            Dict matching the produce_summary JSON schema, containing
            quality attributes, open questions, and pipeline readiness.
        """
        prompt = load_prompt(
            "workshop/produce_summary",
            workshop_context=context.model_dump(),
        )
        raw = await self._llm_client.complete(prompt, response_format="json")
        return json.loads(raw)
