"""Stage 2 classification tool for SpecWeaver."""

from __future__ import annotations

import json
import logging
from collections import Counter

from pydantic import ValidationError

from app.llm.schemas import SCHEMAS
from app.models.contracts import (
    ClassificationCategory,
    ClassifiedRequirement,
    ClassifiedRequirementSet,
    ExtractionResult,
)
from app.pipeline.context import SpecWeaverContext
from app.prompts import load_prompt
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ClassificationTool(BaseTool):
    """
    Stage 2 - Classification Agent.

    Consolidates all extracted requirements into a single classified set. It
    does not perform gap analysis, conflict resolution, or readiness scoring.
    """

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Classify all extracted requirements in one LLM call."""
        extracted_count = sum(
            len(result.extracted_requirements) for result in context.extraction_results
        )
        if extracted_count == 0:
            context.classified_requirements = ClassifiedRequirementSet(
                session_id=context.session_id,
                requirements=[],
                total_count=0,
                by_category={},
                by_confidence={},
            )
            context.completed_stages.append("classification")
            return context

        prompt = load_prompt(
            "classification_agent",
            document_count=len(context.extraction_results),
            extraction_results_json=json.dumps(
                [result.model_dump(mode="json") for result in context.extraction_results],
                indent=2,
            ),
        )

        raw = await self.llm_client.complete(
            prompt,
            output_schema=SCHEMAS["classification"],
            schema_name="classification",
            stage_name="classification",
        )
        try:
            classified = ClassifiedRequirementSet(
                **self._normalize_classification_payload(json.loads(raw))
            )
        except (json.JSONDecodeError, ValidationError) as exc:
            repaired = await self.attempt_repair(
                prompt,
                raw,
                str(exc),
                output_schema=SCHEMAS["classification"],
                schema_name="classification",
                stage_name="classification",
            )
            classified = ClassifiedRequirementSet(
                **self._normalize_classification_payload(json.loads(repaired))
            )

        if not classified.requirements:
            logger.error(
                "classification: empty output despite extracted requirements session=%s",
                context.session_id,
            )
            classified = self._fallback_from_extraction(
                context.session_id,
                context.extraction_results,
            )

        classified = self._detect_obvious_conflicts(classified)

        context.classified_requirements = classified
        context.completed_stages.append("classification")
        logger.info(
            "classification: requirements=%d session=%s",
            len(classified.requirements),
            context.session_id,
        )
        return context

    def _fallback_from_extraction(
        self,
        session_id: str,
        extraction_results: list[ExtractionResult],
    ) -> ClassifiedRequirementSet:
        """Preserve extraction results if classification returns empty."""
        requirements: list[ClassifiedRequirement] = []
        for result in extraction_results:
            for req in result.extracted_requirements:
                requirements.append(
                    ClassifiedRequirement(
                        requirement_id=req.requirement_id,
                        category=self._category_for_type(req.type),
                        statement=req.statement,
                        type=req.type,
                        confidence=req.confidence,
                        is_inferred=req.is_inferred,
                        inference_reasoning=req.inference_reasoning,
                        source_document_ids=[req.source_document_id],
                        source_excerpts=[req.source_excerpt],
                        ambiguities=list(req.ambiguities),
                    )
                )

        by_category = Counter(str(req.category) for req in requirements)
        by_confidence = Counter(str(req.confidence) for req in requirements)
        return ClassifiedRequirementSet(
            session_id=session_id,
            requirements=requirements,
            total_count=len(requirements),
            by_category=dict(by_category),
            by_confidence=dict(by_confidence),
            conflicts=[],
        )

    def _detect_obvious_conflicts(
        self,
        classified: ClassifiedRequirementSet,
    ) -> ClassifiedRequirementSet:
        """Add heuristic conflict entries for obvious mutually exclusive tech choices."""
        tech_requirements = [
            requirement for requirement in classified.requirements
            if str(requirement.type) in {"CONSTRAINT", "NON_FUNCTIONAL", "INTEGRATION"}
        ]

        mutual_exclusions = [
            ({"cosmos", "cosmosdb"}, {"postgresql", "postgres"}),
            ({"aws"}, {"azure", "microsoft azure"}),
            ({"mongodb"}, {"postgresql", "postgres", "mysql"}),
        ]

        detected_conflicts = list(classified.conflicts or [])
        for group_a, group_b in mutual_exclusions:
            reqs_a = [
                req for req in tech_requirements
                if any(token in req.statement.lower() for token in group_a)
            ]
            reqs_b = [
                req for req in tech_requirements
                if any(token in req.statement.lower() for token in group_b)
            ]
            if not reqs_a or not reqs_b:
                continue

            conflict_ids = [req.requirement_id for req in [*reqs_a, *reqs_b]]
            already_recorded = any(
                set(conflict.get("requirement_ids", [])) == set(conflict_ids)
                for conflict in detected_conflicts
            )
            if already_recorded:
                continue

            logger.warning(
                "classification: heuristic conflict detected groupA=%s groupB=%s ids=%s",
                sorted(group_a),
                sorted(group_b),
                conflict_ids,
            )
            detected_conflicts.append(
                {
                    "requirement_ids": conflict_ids,
                    "description": (
                        "Potential technology conflict detected between "
                        f"{sorted(group_a)} and {sorted(group_b)} requirements."
                    ),
                    "interpretations": [],
                    "clarification_question": (
                        "Which technology should be used? "
                        "These options appear mutually exclusive."
                    ),
                }
            )

        return classified.model_copy(update={"conflicts": detected_conflicts})

    def _normalize_classification_payload(self, payload: dict) -> dict:
        """Repair common json_object-mode omissions before validation.

        OpenAI json_object fallback can omit fields that strict schema mode would
        force. We defensively restore required values where a deterministic
        derivation exists.
        """
        requirements = payload.get("requirements")
        if not isinstance(requirements, list):
            payload["requirements"] = []
            requirements = payload["requirements"]

        repaired_missing_categories = 0
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue

            requirement_type = requirement.get("type")
            if requirement_type:
                requirement["type"] = self._canonicalize_requirement_type(requirement_type)

            if requirement.get("category"):
                continue

            if requirement_type:
                requirement["category"] = self._category_for_type(requirement_type).value
                repaired_missing_categories += 1

        if repaired_missing_categories:
            logger.warning(
                "classification: repaired missing category on %d requirement(s)",
                repaired_missing_categories,
            )

        repaired_missing_reasoning = 0
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue

            if not requirement.get("is_inferred"):
                continue

            if requirement.get("inference_reasoning"):
                continue

            source_excerpts = requirement.get("source_excerpts")
            excerpt = "No source excerpt available"
            if isinstance(source_excerpts, list) and source_excerpts:
                first_excerpt = str(source_excerpts[0]).strip()
                if first_excerpt:
                    excerpt = first_excerpt[:200]

            requirement["inference_reasoning"] = (
                "Inferred from the source text: "
                f"'{excerpt}'. "
                "The requirement is implied by this evidence but "
                "was not stated explicitly."
            )
            repaired_missing_reasoning += 1

        if repaired_missing_reasoning:
            logger.warning(
                "classification: repaired missing inference_reasoning on %d inferred requirement(s)",
                repaired_missing_reasoning,
            )

        by_category = Counter(
            str(req.get("category"))
            for req in requirements
            if isinstance(req, dict) and req.get("category")
        )
        by_confidence = Counter(
            str(req.get("confidence"))
            for req in requirements
            if isinstance(req, dict) and req.get("confidence")
        )

        payload["total_count"] = len(requirements)
        payload["by_category"] = dict(by_category)
        payload["by_confidence"] = dict(by_confidence)
        if not isinstance(payload.get("conflicts"), list):
            payload["conflicts"] = []
        return payload

    @staticmethod
    def _category_for_type(requirement_type: str) -> ClassificationCategory:
        """Map requirement type to a Phase 1a fallback category."""
        mapping = {
            "FUNCTIONAL": ClassificationCategory.FUNCTIONAL,
            "NON_FUNCTIONAL": ClassificationCategory.NON_FUNCTIONAL,
            "CONSTRAINT": ClassificationCategory.CONSTRAINTS,
            "ASSUMPTION": ClassificationCategory.ASSUMPTIONS,
            "BUSINESS_RULE": ClassificationCategory.BUSINESS_OBJECTIVES,
            "INTEGRATION": ClassificationCategory.INTEGRATIONS,
            "DATA": ClassificationCategory.DATA_CONSIDERATIONS,
            "OPERATIONAL": ClassificationCategory.NON_FUNCTIONAL,
        }
        return mapping.get(str(requirement_type), ClassificationCategory.FUNCTIONAL)

    @staticmethod
    def _canonicalize_requirement_type(requirement_type: str) -> str:
        """Normalize requirement types to the uppercase enum values expected by validation."""
        normalized = str(requirement_type).strip().upper()
        allowed_types = {
            "FUNCTIONAL",
            "NON_FUNCTIONAL",
            "CONSTRAINT",
            "ASSUMPTION",
            "BUSINESS_RULE",
            "INTEGRATION",
            "DATA",
            "OPERATIONAL",
        }
        return normalized if normalized in allowed_types else "FUNCTIONAL"
