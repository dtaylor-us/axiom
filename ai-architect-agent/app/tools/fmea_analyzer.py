from __future__ import annotations

import json
import logging

from app.models import ArchitectureContext
from app.prompts.loader import load_prompt
from app.tools.base import BaseTool, ToolExecutionException

logger = logging.getLogger(__name__)


class FMEAPlusTool(BaseTool):
    """Performs FMEA+ (Failure Mode and Effects Analysis Plus) on the architecture."""

    async def run(self, context: ArchitectureContext) -> ArchitectureContext:
        if not context.architecture_design:
            raise ToolExecutionException(
                "Cannot perform FMEA without architecture design"
            )

        prompt = load_prompt(
            "fmea_analyzer",
            architecture_design=context.architecture_design,
            components=context.architecture_design.get("components", []),
            characteristics=context.characteristics,
            weaknesses=context.weaknesses,
            trade_offs=context.trade_offs,
            scenarios=context.scenarios,
        )

        raw = await self.llm_client.complete(prompt, response_format="json")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("FMEAPlusTool LLM returned invalid JSON: %s", raw[:500])
            raise ToolExecutionException(
                f"LLM returned invalid JSON: {e}"
            ) from e

        risks = parsed.get("fmea_risks", [])
        validated: list[dict] = []

        for r in risks:
            severity = r.get("severity")
            occurrence = r.get("occurrence")
            detection = r.get("detection")
            rpn = r.get("rpn")

            if not all(
                isinstance(v, int) and 1 <= v <= 10
                for v in (severity, occurrence, detection)
            ):
                logger.warning(
                    "FMEAPlusTool: dropping risk %s — invalid S/O/D values",
                    r.get("id", "unknown"),
                )
                continue

            expected_rpn = severity * occurrence * detection
            if rpn != expected_rpn:
                logger.warning(
                    "FMEAPlusTool: correcting RPN for %s: %s -> %s",
                    r.get("id", "unknown"),
                    rpn,
                    expected_rpn,
                )
                r["rpn"] = expected_rpn

            validated.append(r)

        # Sort by RPN descending
        validated.sort(key=lambda x: x.get("rpn", 0), reverse=True)

        # Extract critical risks (RPN >= 200 or severity >= 9)
        critical_ids = [
            r.get("id", "")
            for r in validated
            if r.get("rpn", 0) >= 200 or r.get("severity", 0) >= 9
        ]

        context.fmea_risks = validated
        context.fmea_critical_risks = critical_ids

        logger.info(
            "FMEAPlusTool produced %d validated risks (%d critical, dropped %d)",
            len(validated),
            len(critical_ids),
            len(risks) - len(validated),
        )
        return context
