from __future__ import annotations

import json
import logging

from app.llm.client import LLMClient
from app.llm.schemas import SCHEMAS
from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)

_STAGE = "requirement_parsing"


class RequirementParserTool(BaseTool):
    """Parses raw requirements into structured entities using the LLM.

    Applies provider-native structured output enforcement (Layer 1) via the
    SCHEMAS registry, and one repair attempt on JSON parse failure (Layer 2).
    """

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.raw_requirements:
            raise ToolExecutionException("raw_requirements is empty; nothing to parse")

        prompt = load_prompt(
            "requirement_parser",
            raw_requirements=context.raw_requirements,
            project_memory_context=json.dumps(
                context.project_memory_context or {},
                indent=2,
                sort_keys=True,
            ),
        )
        if context.iterative_mode and context.previous_architecture:
            prompt = f"""
## ITERATIVE MODE — DELTA UPDATE

The user is refining an existing architecture. The current architecture is:

{_summarise_previous_architecture(context.previous_architecture)}

The user's update request is:
{context.raw_requirements}

INSTRUCTIONS:
- Parse the update request as a DELTA against the current architecture above.
- Preserve all existing components, characteristics, constraints, and decisions
  that the user has NOT asked to change.
- Apply only the changes explicitly requested.
- ADD requests merge with existing components; CHANGE replaces only that element;
  REMOVE excludes only that element.
- NEVER discard existing decisions without an explicit instruction to do so.
- The parsed output must represent the FULL updated system, not just the delta.

{prompt}"""

        raw = await self.llm_client.complete(
            prompt,
            response_format="json",
            output_schema=SCHEMAS.get(_STAGE),
            schema_name=_STAGE,
            stage_name=_STAGE,
        )

        repair_attempted = False
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(
                "RequirementParser JSON parse failed, attempting repair. error=%s", e
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
                parsed = json.loads(raw)
            except json.JSONDecodeError as e2:
                raise ToolExecutionException(
                    f"Stage output could not be parsed after repair attempt. error={e2}"
                ) from e2

        context.parsed_entities = parsed
        logger.info(
            "RequirementParser extracted domain=%s, system_type=%s, %d FRs "
            "repair_attempted=%s",
            parsed.get("domain", "unknown"),
            parsed.get("system_type", "unknown"),
            len(parsed.get("functional_requirements", [])),
            repair_attempted,
        )
        return context


def _summarise_previous_architecture(prev: dict) -> str:
    """Return a compact requirement-parsing view of a previous design."""
    components = prev.get("components", [])
    characteristics = prev.get("characteristics", [])
    component_lines = []
    for component in components[:20]:
        name = component.get("name", "") if isinstance(component, dict) else str(component)
        responsibility = component.get("responsibility", "") if isinstance(component, dict) else ""
        component_lines.append(
            f"  - {name}: {responsibility}" if responsibility else f"  - {name}"
        )
    characteristic_lines = []
    for characteristic in characteristics[:10]:
        name = characteristic.get("name", "") if isinstance(characteristic, dict) else str(characteristic)
        characteristic_lines.append(f"  - {name}")
    formatted_components = "\n".join(component_lines) or "  (none)"
    formatted_characteristics = "\n".join(characteristic_lines) or "  (none)"
    return (
        f"Architecture style: {prev.get('style', 'Unknown')}\n"
        f"Domain: {prev.get('domain', '')}\n\n"
        f"Components ({len(components)} total):\n"
        f"{formatted_components}\n\n"
        f"Quality attributes:\n"
        f"{formatted_characteristics}"
    )
