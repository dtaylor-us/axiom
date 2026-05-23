"""Requirement challenge stage with context budgeting and schema enforcement."""

from __future__ import annotations

import json
import logging
import os

from app.llm.budget import budget_json_list, get_input_budget
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "requirement_challenge"
_PRIORITY_FIELDS = {
    "functional_requirements": 0,
    "non_functional_requirements": 1,
    "constraints": 2,
    "assumptions": 3,
}


class RequirementChallengeEngineTool(BaseTool):
    """Challenges the parsed requirements to find gaps and ambiguities.

    Applies provider-native structured output enforcement (Layer 1) via the
    SCHEMAS registry, and one repair attempt on JSON parse failure (Layer 2).
    """

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """
        Challenge parsed requirements and write the findings to context.

        Args:
            context: Pipeline state after requirement parsing.

        Returns:
            Updated context with challenge findings.

        Raises:
            ToolExecutionException: If prerequisites are missing or JSON cannot
                be parsed after the single repair attempt.
        """
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        provider = os.getenv("LLM_PROVIDER", "ollama")
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX_PRIMARY", "16384"))
        input_budget = get_input_budget(_STAGE, provider, num_ctx)
        budgeted_entities = _budget_parsed_entities(
            context.parsed_entities,
            max_tokens=input_budget,
            conversation_id=context.conversation_id,
        )

        prompt = load_prompt(
            "requirement_challenge",
            raw_requirements=context.raw_requirements,
            parsed_entities=budgeted_entities,
            review_constraints=context.review_constraints,
        )

        raw = await self.llm_client.complete(
            prompt,
            response_format="json",
            output_schema=SCHEMAS.get(_STAGE),
            schema_name=_STAGE,
            stage_name=_STAGE,
        )

        repair_attempted = False
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(
                "ChallengeEngine JSON parse failed, attempting repair. error=%s", e
            )
            repair_attempted = True
            raw = await self.attempt_repair(
                original_prompt=prompt,
                failed_response=raw,
                error_description=f"Invalid JSON: {e}",
                output_schema=SCHEMAS.get(_STAGE),
                schema_name=_STAGE,
                stage_name=_STAGE,
            )
            try:
                result = json.loads(raw)
            except json.JSONDecodeError as e2:
                raise ToolExecutionException(
                    "Stage output could not be parsed after invalid JSON "
                    f"repair attempt. error={e2}"
                ) from e2

        context.missing_requirements = result.get("missing_requirements", [])
        context.ambiguities = result.get("ambiguities", [])
        context.hidden_assumptions = result.get("hidden_assumptions", [])
        context.clarifying_questions = result.get("clarifying_questions", [])

        context.architecture_override = result.get(
            "architecture_override",
            {
                "type": "none",
                "styles": [],
                "raw_instruction": "",
                "detected_confidence": "low",
            },
        )
        context.buy_vs_build_preferences = result.get(
            "buy_vs_build_preferences",
            {
                "prefer_open_source": False,
                "avoid_vendor_lockin": False,
                "existing_tools": [],
                "build_preference": "neutral",
                "budget_constrained": False,
                "raw_signals": [],
            },
        )

        logger.info(
            "ChallengeEngine found %d missing reqs, %d ambiguities, "
            "%d assumptions, %d questions repair_attempted=%s",
            len(context.missing_requirements),
            len(context.ambiguities),
            len(context.hidden_assumptions),
            len(context.clarifying_questions),
            repair_attempted,
        )
        return context


def _budget_parsed_entities(
    parsed_entities: dict,
    max_tokens: int,
    conversation_id: str,
) -> dict:
    """
    Budget requirement lists before the challenge prompt is rendered.

    Args:
        parsed_entities: Requirement parser output.
        max_tokens: Token budget for list-valued requirement fields.
        conversation_id: Conversation identifier for truncation logs.

    Returns:
        Copy of parsed_entities with list fields trimmed by priority.
    """
    list_entries: list[dict] = []
    budgeted = {
        key: ([] if isinstance(value, list) else value)
        for key, value in parsed_entities.items()
    }

    for field_name, value in parsed_entities.items():
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            list_entries.append({
                "field_name": field_name,
                "index": index,
                "item": item,
                "priority": _PRIORITY_FIELDS.get(field_name, 4),
            })

    ordered_entries = sorted(
        list_entries,
        key=lambda entry: (entry["priority"], entry["index"]),
    )
    compact_entries = [
        {"field_name": entry["field_name"], "item": entry["item"]}
        for entry in ordered_entries
    ]
    kept_entries = budget_json_list(
        compact_entries,
        max_tokens=max_tokens,
        stage_name=_STAGE,
        item_label="requirements",
    )

    for entry in kept_entries:
        budgeted[entry["field_name"]].append(entry["item"])

    if len(kept_entries) < len(list_entries):
        logger.info(
            "requirement_challenge: budgeted %d of %d requirements for "
            "context window. conversation_id=%s",
            len(kept_entries),
            len(list_entries),
            conversation_id,
        )

    return budgeted
