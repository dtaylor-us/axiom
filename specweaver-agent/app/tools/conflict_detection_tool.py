"""Structured contradiction detection for SpecWeaver Phase 1b."""

from __future__ import annotations

import json
import logging
import time
import uuid

from app.llm.client import LLMCallException
from app.llm.schemas import SCHEMAS
from app.models.contracts import (
    ClassifiedRequirementSet,
    ConflictDetectionResult,
    ConflictItem,
)
from app.pipeline.context import SpecWeaverContext
from app.prompts import load_prompt
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

OVERLAP_DUPLICATE_RATIO = 0.5

MUTUAL_EXCLUSIONS = [
    {
        "group_a": {"cosmos", "cosmosdb"},
        "group_b": {"postgresql", "postgres"},
        "topic": "database technology",
        "question": "Which database must be used?",
    },
    {
        "group_a": {"cloud-agnostic", "cloud agnostic", "multi-cloud"},
        "group_b": {
            "azure only",
            "must be on azure",
            "deployed on azure",
            "microsoft azure",
            "strategic partnership",
        },
        "topic": "cloud strategy",
        "question": "Is the system cloud-agnostic or Azure-specific?",
    },
    {
        "group_a": {"aws"},
        "group_b": {"azure", "microsoft azure"},
        "topic": "cloud provider",
        "question": "Which cloud provider must be used?",
    },
    {
        "group_a": {"real-time", "real time", "websocket", "streaming"},
        "group_b": {"polling", "poll every", "batch"},
        "topic": "data freshness approach",
        "question": "Should the system use real-time streaming or polling?",
    },
]


class ConflictDetectionTool(BaseTool):
    """Detect requirement conflicts without resolving either side."""

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Run heuristic detection before adding LLM-discovered conflicts."""
        started_at = time.monotonic()
        if not context.classified_requirements:
            context.completed_stages.append("conflict_detection")
            logger.info(
                "conflict_detection: duration_ms=%d session=%s",
                int((time.monotonic() - started_at) * 1000),
                context.session_id,
            )
            return context

        heuristic_conflicts = self._run_heuristics(context.classified_requirements)
        llm_conflicts = await self._run_llm_analysis(
            context.session_id,
            context.classified_requirements,
        )
        conflicts = self._merge_conflicts(heuristic_conflicts, llm_conflicts)

        context.conflict_detection_result = ConflictDetectionResult(
            session_id=context.session_id,
            conflicts=conflicts,
            conflict_count=len(conflicts),
        )
        logger.info(
            "conflict_detection: found %d conflicts session=%s",
            len(conflicts),
            context.session_id,
        )
        context.completed_stages.append("conflict_detection")
        logger.info(
            "conflict_detection: duration_ms=%d session=%s",
            int((time.monotonic() - started_at) * 1000),
            context.session_id,
        )
        return context

    def _run_heuristics(
        self,
        classified: ClassifiedRequirementSet,
    ) -> list[ConflictItem]:
        """Find known mutually exclusive technology and policy positions."""
        conflicts: list[ConflictItem] = []
        requirements = classified.requirements

        for exclusion in MUTUAL_EXCLUSIONS:
            requirements_a = self._matching_requirements(
                classified,
                set(exclusion["group_a"]),
            )
            requirements_b = self._matching_requirements(
                classified,
                set(exclusion["group_b"]),
            )
            if not requirements_a or not requirements_b:
                continue

            conflict_ids = [
                requirement.requirement_id
                for requirement in [*requirements_a, *requirements_b]
            ]
            conflicts.append(
                ConflictItem(
                    conflict_id=str(uuid.uuid4()),
                    requirement_ids=conflict_ids,
                    description=(
                        f"Conflicting {exclusion['topic']} requirements detected. "
                        "Stakeholders have specified mutually exclusive positions."
                    ),
                    interpretations=[
                        (
                            f"Apply position A ({sorted(exclusion['group_a'])[0]}): "
                            "implications must be assessed."
                        ),
                        (
                            f"Apply position B ({sorted(exclusion['group_b'])[0]}): "
                            "implications must be assessed."
                        ),
                    ],
                    clarification_question=str(exclusion["question"]),
                )
            )

        return conflicts

    async def _run_llm_analysis(
        self,
        session_id: str,
        classified: ClassifiedRequirementSet,
    ) -> list[ConflictItem]:
        """Ask the LLM for semantic contradictions missed by heuristics."""
        prompt = load_prompt(
            "conflict_detection",
            session_id=session_id,
            requirements_json=json.dumps(
                [requirement.model_dump(mode="json") for requirement in classified.requirements],
                indent=2,
            ),
        )

        try:
            raw = await self.llm_client.complete(
                prompt,
                output_schema=SCHEMAS["conflict_detection"],
                schema_name="conflict_detection",
                stage_name="conflict_detection",
            )
            parsed = json.loads(raw)
        except (json.JSONDecodeError, KeyError, LLMCallException, ValueError) as exc:
            logger.warning(
                "conflict_detection: LLM pass failed. Heuristic results only. "
                "error=%s session=%s",
                str(exc),
                session_id,
            )
            return []

        return [
            ConflictItem(
                conflict_id=str(uuid.uuid4()),
                requirement_ids=list(conflict.get("requirement_ids", [])),
                description=str(conflict.get("description", "")),
                interpretations=list(conflict.get("interpretations", [])),
                clarification_question=str(
                    conflict.get("clarification_question", "")
                ),
            )
            for conflict in parsed.get("conflicts", [])
            if conflict.get("requirement_ids") and conflict.get("description")
        ]

    def _merge_conflicts(
        self,
        heuristic: list[ConflictItem],
        llm_list: list[ConflictItem],
    ) -> list[ConflictItem]:
        """Merge conflicts, deduplicating by significant requirement overlap."""
        conflicts = list(heuristic)
        existing_id_sets = [set(conflict.requirement_ids) for conflict in heuristic]

        for conflict in llm_list:
            new_ids = set(conflict.requirement_ids)
            is_duplicate = any(
                len(new_ids & existing_ids) / max(len(new_ids), len(existing_ids))
                > OVERLAP_DUPLICATE_RATIO
                for existing_ids in existing_id_sets
                if new_ids or existing_ids
            )
            if is_duplicate:
                continue

            conflicts.append(conflict)
            existing_id_sets.append(new_ids)

        return conflicts

    @staticmethod
    def _matching_requirements(
        classified: ClassifiedRequirementSet,
        tokens: set[str],
    ):
        """Return requirements whose statement contains any token."""
        return [
            requirement
            for requirement in classified.requirements
            if any(token in requirement.statement.lower() for token in tokens)
        ]
