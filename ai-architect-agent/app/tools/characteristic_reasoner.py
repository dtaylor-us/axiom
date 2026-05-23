"""Characteristic inference stage with context budgeting and empty-output retry."""

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

_STAGE = "characteristic_inference"
_REQUIREMENT_FIELDS = (
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "entities",
    "integration_points",
)


class CharacteristicReasoningEngineTool(BaseTool):
    """Infers architecture characteristics from requirements and scenarios."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        """
        Infer architecture characteristics and write them to context.

        Args:
            context: Pipeline state after scenario modeling.

        Returns:
            Updated context with inferred characteristics.

        Raises:
            ToolExecutionException: If prerequisites are missing, JSON cannot
                be repaired, or both inference attempts return no characteristics.
        """
        if not context.parsed_entities:
            raise ToolExecutionException(
                "parsed_entities is empty; run RequirementParser first"
            )

        provider = os.getenv("LLM_PROVIDER", "ollama")
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX_PRIMARY", "16384"))
        input_budget = get_input_budget(_STAGE, provider, num_ctx)
        budgeted_scenarios = budget_json_list(
            context.scenarios or [],
            max_tokens=input_budget // 2,
            stage_name=_STAGE,
            item_label="scenarios",
        )
        budgeted_entities = _budget_parsed_entities(
            context.parsed_entities,
            max_tokens=input_budget // 3,
        )

        prompt = load_prompt(
            "characteristic_reasoner",
            raw_requirements=context.raw_requirements,
            parsed_entities=budgeted_entities,
            scenarios=budgeted_scenarios,
        )

        result, raw, repair_attempted = await self._complete_and_parse(prompt)
        characteristics = result.get("characteristics", [])

        if not characteristics:
            logger.warning(
                "characteristic_inference returned empty characteristics. "
                "response_len=%d raw='%s'. Retrying with simplified input. "
                "conversation_id=%s",
                len(raw),
                raw[:100],
                context.conversation_id,
            )
            retry_prompt = load_prompt(
                "characteristic_reasoner",
                raw_requirements=context.raw_requirements,
                parsed_entities=_budget_parsed_entities(
                    context.parsed_entities,
                    max_tokens=max(1, input_budget // 6),
                    max_items=5,
                ),
                scenarios=budgeted_scenarios[:3],
            )
            retry_result, retry_raw, _ = await self._complete_and_parse(retry_prompt)
            characteristics = retry_result.get("characteristics", [])

            if not characteristics:
                raise ToolExecutionException(
                    "characteristic_inference returned empty output on both "
                    "attempts. This is likely a context overflow or JSON "
                    "schema compliance failure under memory pressure. Ensure "
                    "Ollama is running natively on macOS (brew install ollama) "
                    "and not inside Docker."
                )

            raw = retry_raw
            logger.info(
                "characteristic_inference retry succeeded. characteristics=%d "
                "conversation_id=%s",
                len(characteristics),
                context.conversation_id,
            )

        context.characteristics = characteristics
        logger.info(
            "CharacteristicReasoningEngine inferred %d characteristics "
            "repair_attempted=%s response_len=%d",
            len(context.characteristics),
            repair_attempted,
            len(raw),
        )
        return context

    async def _complete_and_parse(self, prompt: str) -> tuple[dict, str, bool]:
        """
        Complete a prompt and parse JSON with the standard single repair.

        Args:
            prompt: Rendered characteristic inference prompt.

        Returns:
            Parsed response, raw response, and whether repair was attempted.

        Raises:
            ToolExecutionException: If JSON parsing fails after repair.
        """
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
        except json.JSONDecodeError as exc:
            logger.warning(
                "CharacteristicReasoningEngine JSON parse failed, "
                "attempting repair. error=%s",
                exc,
            )
            repair_attempted = True
            raw = await self.attempt_repair(
                original_prompt=prompt,
                failed_response=raw,
                error_description=f"Invalid JSON: {exc}",
                output_schema=SCHEMAS.get(_STAGE),
                schema_name=_STAGE,
                stage_name=_STAGE,
            )
            try:
                result = json.loads(raw)
            except json.JSONDecodeError as repair_exc:
                raise ToolExecutionException(
                    "Stage output could not be parsed after invalid JSON "
                    "repair attempt. "
                    f"error={repair_exc}"
                ) from repair_exc

        return result, raw, repair_attempted


def _budget_parsed_entities(
    parsed_entities: dict,
    max_tokens: int,
    max_items: int | None = None,
) -> dict:
    """
    Budget parsed requirement lists used by characteristic inference.

    Args:
        parsed_entities: Requirement parser output.
        max_tokens: Token budget for list-valued requirement fields.
        max_items: Optional hard cap across all requirement items.

    Returns:
        Copy of parsed_entities with long list fields trimmed.
    """
    budgeted = dict(parsed_entities)
    requirement_items: list[dict] = []

    for field_name in _REQUIREMENT_FIELDS:
        value = parsed_entities.get(field_name, [])
        if not isinstance(value, list):
            continue
        for item in value:
            requirement_items.append({"field_name": field_name, "item": item})
        budgeted[field_name] = []

    if max_items is not None:
        requirement_items = requirement_items[:max_items]

    kept_items = budget_json_list(
        requirement_items,
        max_tokens=max_tokens,
        stage_name=_STAGE,
        item_label="requirements",
    )
    for entry in kept_items:
        budgeted[entry["field_name"]].append(entry["item"])

    return budgeted
