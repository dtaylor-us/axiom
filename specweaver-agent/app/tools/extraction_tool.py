"""Stage 1 extraction tool for SpecWeaver."""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.llm.client import LLMCallException
from app.llm.schemas import SCHEMAS
from app.models.contracts import DocumentPayload, ExtractionResult
from app.pipeline.context import SpecWeaverContext
from app.prompts import load_prompt
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Keep the retry payload small when the first JSON parse fails because
# overlong prompts are a common cause of truncated model output.
MAX_RETRY_CONTENT_CHARS = 3000


class ExtractionTool(BaseTool):
    """
    Stage 1 - Extraction Agent.

    Processes each document independently. A single document failure is recorded
    in pipeline_errors but does not stop remaining documents from being handled.
    """

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Extract requirements from every document in the context."""
        for doc in context.documents:
            try:
                result = await self._extract_document(context.session_id, doc)
                context.extraction_results.append(result)
                logger.info(
                    "extraction: document=%s requirements=%d session=%s",
                    doc.document_id,
                    len(result.extracted_requirements),
                    context.session_id,
                )
            except Exception as exc:
                logger.error(
                    "extraction: failed document=%s error=%s session=%s",
                    doc.document_id,
                    str(exc),
                    context.session_id,
                )
                context.pipeline_errors.append(
                    f"Extraction failed for document {doc.document_id}: {str(exc)}"
                )

        context.completed_stages.append("extraction")
        return context

    async def _extract_document(
        self,
        session_id: str,
        doc: DocumentPayload,
    ) -> ExtractionResult:
        """Call the LLM for a single document and validate the result."""
        try:
            result = await self._attempt_extraction(session_id, doc, doc.content)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            logger.warning(
                "extraction: parse/validation failed document=%s session=%s "
                "retry=truncated error=%s",
                doc.document_id,
                session_id,
                str(exc)[:160],
            )
            truncated_content = self._truncate_content_for_retry(doc.content)
            try:
                result = await self._attempt_extraction(
                    session_id,
                    doc,
                    truncated_content,
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as retry_exc:
                raise ValueError(
                    "LLM extraction remained invalid after truncated retry"
                ) from retry_exc

        if not result.extracted_requirements:
            logger.warning(
                "extraction: zero requirements document=%s session=%s",
                doc.document_id,
                session_id,
            )
        return result

    async def _attempt_extraction(
        self,
        session_id: str,
        doc: DocumentPayload,
        content: str,
    ) -> ExtractionResult:
        """Run one extraction attempt for the provided document content."""
        prompt = load_prompt(
            "extraction_agent",
            session_id=session_id,
            document_id=doc.document_id,
            document_type=doc.document_type,
            content=content,
            source_label=doc.source_label or "Not provided",
        )

        raw = await self._complete_extraction(prompt, doc.document_id, session_id)
        if self._is_empty_response(raw):
            logger.warning(
                "extraction: empty response document=%s session=%s retry=true",
                doc.document_id,
                session_id,
            )
            raw = await self._complete_extraction(
                self._simplified_prompt(session_id, doc),
                doc.document_id,
                session_id,
            )
        if self._is_empty_response(raw):
            raise ValueError("LLM returned empty extraction response after retry")

        parsed = json.loads(raw)
        result = ExtractionResult(**parsed)
        return self._validate_and_repair(result)

    async def _complete_extraction(
        self,
        prompt: str,
        document_id: str,
        session_id: str,
    ) -> str:
        """Call the LLM, retrying once when the provider reports empty output."""
        try:
            return await self.llm_client.complete(
                prompt,
                output_schema=SCHEMAS["extraction"],
                schema_name="extraction",
                stage_name="extraction",
            )
        except LLMCallException as exc:
            if "empty response" not in str(exc).lower():
                raise
            logger.warning(
                "extraction: empty provider response document=%s session=%s retry=true",
                document_id,
                session_id,
            )
            return ""

    def _validate_and_repair(self, result: ExtractionResult) -> ExtractionResult:
        """Validate and repair extraction output where safe.

        Args:
            result: Parsed extraction result for one document.

        Returns:
            ExtractionResult with minimal safe repairs applied.
        """
        repaired_requirements = []
        for req in result.extracted_requirements:
            repaired_req = req

            if req.is_inferred and not req.inference_reasoning:
                logger.warning(
                    "extraction: requirement %s is inferred but has no "
                    "inference_reasoning - synthesising from source excerpt",
                    req.requirement_id,
                )
                excerpt = (req.source_excerpt or "").strip()[:200]
                if not excerpt:
                    excerpt = "No source excerpt available"
                repaired_req = req.model_copy(
                    update={
                        "inference_reasoning": (
                            "Inferred from the source text: "
                            f"'{excerpt}'. "
                            "The requirement is implied by this evidence but "
                            "was not stated explicitly."
                        )
                    }
                )

            if not req.source_excerpt or not req.source_excerpt.strip():
                logger.warning(
                    "extraction: requirement %s has empty source_excerpt - "
                    "traceability violation",
                    req.requirement_id,
                )

            repaired_requirements.append(repaired_req)

        return result.model_copy(update={"extracted_requirements": repaired_requirements})

    @staticmethod
    def _truncate_content_for_retry(content: str) -> str:
        """Reduce content size for one parse-failure retry attempt."""
        trimmed = content[:MAX_RETRY_CONTENT_CHARS]
        if len(trimmed) < len(content):
            return (
                f"{trimmed}\n\n"
                "[Document truncated for extraction retry due to malformed "
                "JSON in the first attempt.]"
            )
        return trimmed

    @staticmethod
    def _simplified_prompt(session_id: str, doc: DocumentPayload) -> str:
        """Build the one-retry fallback prompt for empty extraction output."""
        return (
            "Extract requirements from this document and return only valid JSON "
            "matching the extraction schema. Include session_id, document_id, "
            "extracted_requirements, and extraction_notes.\n\n"
            f"session_id: {session_id}\n"
            f"document_id: {doc.document_id}\n"
            f"document_type: {doc.document_type}\n"
            f"content:\n{doc.content}"
        )

    @staticmethod
    def _is_empty_response(raw: str | None) -> bool:
        """Return whether an LLM response is empty."""
        return not raw or not raw.strip()
