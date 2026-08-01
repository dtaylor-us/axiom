"""Stage 3 ArchInputPackage formatter for SpecWeaver."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from app.models.contracts import ArchInputPackage, ConfidenceLevel
from app.pipeline.context import SpecWeaverContext
from app.prompts import load_prompt
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class OutputFormatterTool(BaseTool):
    """
    Stage 3 - Output Formatter.

    The LLM is used only to derive system_description. Requirements and Phase
    1a defaults are assembled deterministically from classified requirements.
    """

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Build the final ArchInputPackage."""
        if context.classified_requirements is None:
            raise ValueError("Output formatting requires classified requirements")

        logger.info(
            "output_formatting: starting gaps=%d conflicts=%d duplicates=%d "
            "requirements=%d session=%s",
            len(context.gap_analysis_result.gaps)
            if context.gap_analysis_result
            else -1,
            len(context.conflict_detection_result.conflicts)
            if context.conflict_detection_result
            else -1,
            context.consolidation_result.duplicate_count
            if context.consolidation_result
            else -1,
            len(context.classified_requirements.requirements),
            context.session_id,
        )

        classified = context.classified_requirements
        prompt = load_prompt(
            "output_formatter",
            classified_requirements_json=json.dumps(
                classified.model_dump(mode="json"),
                indent=2,
            ),
            document_count=len(context.documents),
            total_requirements=len(classified.requirements),
        )
        raw = await self.llm_client.complete(
            prompt,
            output_schema=None,
            schema_name="output_formatting",
            stage_name="output_formatting",
        )
        system_description = self._extract_system_description(raw)
        requirements = list(classified.requirements)
        gaps = (
            list(context.gap_analysis_result.gaps)
            if context.gap_analysis_result
            else []
        )
        conflicts = (
            list(context.conflict_detection_result.conflicts)
            if context.conflict_detection_result
            else []
        )
        duplicate_count = (
            context.consolidation_result.duplicate_count
            if context.consolidation_result
            else 0
        )
        context.arch_input_package = ArchInputPackage(
            package_id=str(uuid.uuid4()),
            session_id=context.session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            readiness_score=0.0,
            system_description=system_description,
            requirements=requirements,
            gaps=gaps,
            conflicts=conflicts,
            source_documents=[
                {
                    "document_id": doc.document_id,
                    "document_type": doc.document_type,
                    "filename": doc.filename,
                    "source_label": doc.source_label,
                }
                for doc in context.documents
            ],
            total_requirements=len(requirements),
            high_confidence_count=sum(
                1 for req in requirements if req.confidence == ConfidenceLevel.HIGH
            ),
            inferred_count=sum(1 for req in requirements if req.is_inferred),
            duplicate_count=duplicate_count,
            gap_count=len(gaps),
            conflict_count=len(conflicts),
        )
        context.completed_stages.append("output_formatting")
        logger.info(
            "output_formatting: requirements=%d gaps=%d conflicts=%d duplicates=%d session=%s",
            context.arch_input_package.total_requirements,
            context.arch_input_package.gap_count,
            context.arch_input_package.conflict_count,
            context.arch_input_package.duplicate_count,
            context.session_id,
        )
        return context

    @staticmethod
    def _extract_system_description(raw: str) -> str:
        """Parse the LLM's system_description-only response."""
        if not raw or not raw.strip():
            return "Requirements package generated from supplied source documents."
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip()
        return (
            str(parsed.get("system_description") or "").strip()
            or "Requirements package generated from supplied source documents."
        )
