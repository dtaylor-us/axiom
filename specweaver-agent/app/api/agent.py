"""SpecWeaver agent API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.llm.client import get_llm_client
from app.models.contracts import ExtractionRequest, ExtractionResponse
from app.pipeline.context import SpecWeaverContext
from app.pipeline.graph import build_graph, coerce_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/agent/extract", response_model=ExtractionResponse)
async def extract(
    request: ExtractionRequest,
    llm_client=Depends(get_llm_client),
) -> ExtractionResponse:
    """
    Run the three-stage extraction pipeline synchronously for specweaver-api.
    """
    try:
        graph = build_graph(llm_client)
        context = SpecWeaverContext(
            session_id=request.session_id,
            documents=request.documents,
            project_memory_context=request.project_memory_context,
        )
        result = coerce_context(await graph.ainvoke(context))

        if result.arch_input_package is None:
            raise ValueError(
                "Pipeline completed but produced no package. "
                f"Errors: {result.pipeline_errors}"
            )

        logger.info(
            "pipeline: complete stages=%s gaps=%d conflicts=%d requirements=%d duplicates=%d session=%s",
            result.completed_stages,
            len(result.gap_analysis_result.gaps)
            if result.gap_analysis_result
            else 0,
            len(result.conflict_detection_result.conflicts)
            if result.conflict_detection_result
            else 0,
            result.arch_input_package.total_requirements,
            result.consolidation_result.duplicate_count
            if result.consolidation_result
            else 0,
            request.session_id,
        )

        package_json = result.arch_input_package.model_dump_json(by_alias=True)
        logger.info(
            "extract: complete session=%s requirements=%d documents=%d",
            request.session_id,
            result.arch_input_package.total_requirements,
            len(request.documents),
        )
        return ExtractionResponse(
            session_id=request.session_id,
            arch_input_package_json=package_json,
            success=True,
        )

    except Exception as exc:
        logger.error(
            "extract: failed session=%s error=%s",
            request.session_id,
            str(exc),
        )
        return ExtractionResponse(
            session_id=request.session_id,
            arch_input_package_json="",
            success=False,
            error_message=str(exc),
        )
