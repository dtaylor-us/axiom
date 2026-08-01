"""Vector-based semantic deduplication for SpecWeaver requirements."""

from __future__ import annotations

import logging
import os
import time
import uuid

import httpx
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.models.contracts import (
    ConfidenceLevel,
    ConsolidationGroup,
    ConsolidationResult,
    ExtractedRequirement,
    ExtractionResult,
)
from app.pipeline.context import SpecWeaverContext
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

# A high duplicate threshold avoids false-positive merges, which are more
# damaging than leaving a duplicate for downstream review.
DUPLICATE_THRESHOLD = 0.92
DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_SEARCH_LIMIT = 10


class ConsolidationTool(BaseTool):
    """Consolidate semantically duplicate requirements using Qdrant vectors."""

    def __init__(
        self,
        llm_client,
        qdrant_url: str = "http://qdrant:6333",
    ) -> None:
        """Create a consolidation tool.

        Args:
            llm_client: LLM client retained for BaseTool tracing consistency.
            qdrant_url: URL for the Qdrant vector database.
        """
        super().__init__(llm_client)
        self.qdrant = QdrantClient(url=qdrant_url, check_compatibility=False)

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Deduplicate extracted requirements and update downstream extraction state."""
        started_at = time.monotonic()
        all_requirements = [
            requirement
            for result in context.extraction_results
            for requirement in result.extracted_requirements
        ]

        if not all_requirements:
            logger.warning(
                "consolidation: no requirements to consolidate. session=%s",
                context.session_id,
            )
            context.completed_stages.append("consolidation")
            logger.info(
                "consolidation: duration_ms=%d session=%s",
                int((time.monotonic() - started_at) * 1000),
                context.session_id,
            )
            return context

        collection_name = self._collection_name(context.session_id)
        try:
            result = await self._consolidate(
                context.session_id,
                all_requirements,
                collection_name,
            )
            context.consolidation_result = result
            context.extraction_results = [
                ExtractionResult(
                    session_id=context.session_id,
                    document_id="consolidated",
                    extracted_requirements=result.merged_requirements,
                    extraction_notes=[
                        "Requirements consolidated by vector similarity."
                    ],
                )
            ]
            logger.info(
                "consolidation: original=%d merged=%d duplicates_removed=%d "
                "session=%s",
                result.original_count,
                result.consolidated_count,
                result.duplicate_count,
                context.session_id,
            )
        finally:
            self._delete_collection(collection_name)

        context.completed_stages.append("consolidation")
        logger.info(
            "consolidation: duration_ms=%d session=%s",
            int((time.monotonic() - started_at) * 1000),
            context.session_id,
        )
        return context

    async def _consolidate(
        self,
        session_id: str,
        requirements: list[ExtractedRequirement],
        collection_name: str,
    ) -> ConsolidationResult:
        """Embed, index, group, and merge semantically duplicate requirements."""
        embeddings = await self._embed_requirements(requirements)
        self._create_collection(collection_name, len(embeddings[0]))
        self._store_embeddings(collection_name, requirements, embeddings)
        groups = self._find_duplicate_groups(collection_name, requirements, embeddings)
        merged = self._merge_groups(groups, requirements)

        return ConsolidationResult(
            session_id=session_id,
            consolidated_groups=groups,
            merged_requirements=merged,
            duplicate_count=len(requirements) - len(merged),
            original_count=len(requirements),
            consolidated_count=len(merged),
        )

    async def _embed_requirements(
        self,
        requirements: list[ExtractedRequirement],
    ) -> list[list[float]]:
        """Generate one embedding per requirement statement using the active provider."""
        provider_name = os.getenv("LLM_PROVIDER", "ollama").lower()
        if provider_name == "openai":
            embedding_model = os.getenv(
                "OPENAI_EMBEDDING_MODEL",
                DEFAULT_OPENAI_EMBEDDING_MODEL,
            )
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = await client.embeddings.create(
                model=embedding_model,
                input=[requirement.statement for requirement in requirements],
            )
            return [item.embedding for item in response.data]

        embedding_model = os.getenv(
            "SPECWEAVER_EMBEDDING_MODEL",
            DEFAULT_OLLAMA_EMBEDDING_MODEL,
        )
        ollama_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            for requirement in requirements:
                response = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={
                        "model": embedding_model,
                        "prompt": requirement.statement,
                    },
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])

        return embeddings

    def _create_collection(self, collection_name: str, vector_dimension: int) -> None:
        """Create a fresh temporary Qdrant collection for the session."""
        try:
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_dimension,
                    distance=Distance.COSINE,
                ),
            )
        except Exception as exc:
            logger.warning(
                "consolidation: recreating temporary collection=%s error=%s",
                collection_name,
                str(exc),
            )
            self.qdrant.delete_collection(collection_name)
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_dimension,
                    distance=Distance.COSINE,
                ),
            )

    def _store_embeddings(
        self,
        collection_name: str,
        requirements: list[ExtractedRequirement],
        embeddings: list[list[float]],
    ) -> None:
        """Store requirement embeddings in Qdrant with trace payloads."""
        points = [
            PointStruct(
                id=index,
                vector=embedding,
                payload={
                    "requirement_id": requirement.requirement_id,
                    "statement": requirement.statement,
                    "type": self._enum_value(requirement.type),
                    "confidence": self._enum_value(requirement.confidence),
                },
            )
            for index, (requirement, embedding) in enumerate(
                zip(requirements, embeddings)
            )
        ]
        self.qdrant.upsert(collection_name=collection_name, points=points)

    def _find_duplicate_groups(
        self,
        collection_name: str,
        requirements: list[ExtractedRequirement],
        embeddings: list[list[float]],
    ) -> list[ConsolidationGroup]:
        """Group requirements connected by duplicate-threshold similarity."""
        parent = list(range(len(requirements)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left_index: int, right_index: int) -> None:
            parent[find(left_index)] = find(right_index)

        for index, embedding in enumerate(embeddings):
            response = self.qdrant.query_points(
                collection_name=collection_name,
                query=embedding,
                limit=SIMILARITY_SEARCH_LIMIT,
                score_threshold=DUPLICATE_THRESHOLD,
            )
            results = response.points
            for result in results:
                match_index = int(result.id)
                if match_index != index:
                    union(index, match_index)

        groups_by_root: dict[int, list[int]] = {}
        for index in range(len(requirements)):
            groups_by_root.setdefault(find(index), []).append(index)

        return [
            ConsolidationGroup(
                group_id=str(uuid.uuid4()),
                requirements=[requirements[index] for index in indices],
                similarity_score=self._average_similarity(
                    collection_name,
                    embeddings,
                    indices,
                ),
                is_duplicate_group=len(indices) > 1,
            )
            for indices in groups_by_root.values()
        ]

    def _average_similarity(
        self,
        collection_name: str,
        embeddings: list[list[float]],
        indices: list[int],
    ) -> float:
        """Calculate pairwise average similarity for a group."""
        if len(indices) == 1:
            return 1.0

        similarities: list[float] = []
        for left_position, left_index in enumerate(indices):
            response = self.qdrant.query_points(
                collection_name=collection_name,
                query=embeddings[left_index],
                limit=len(embeddings),
            )
            results = response.points
            for right_index in indices[left_position + 1:]:
                score = next(
                    (result.score for result in results if int(result.id) == right_index),
                    0.0,
                )
                similarities.append(score)

        return sum(similarities) / len(similarities) if similarities else 1.0

    def _merge_groups(
        self,
        groups: list[ConsolidationGroup],
        requirements: list[ExtractedRequirement],
    ) -> list[ExtractedRequirement]:
        """Merge duplicate groups while preserving all traceability evidence."""
        merged: list[ExtractedRequirement] = []
        for group in groups:
            if not group.is_duplicate_group:
                merged.extend(group.requirements)
                continue

            requirements_in_group = group.requirements
            source_excerpts = list(
                {
                    requirement.source_excerpt
                    for requirement in requirements_in_group
                    if requirement.source_excerpt
                }
            )
            is_inferred = any(
                requirement.is_inferred for requirement in requirements_in_group
            )
            reasoning = self._combine_inference_reasoning(
                requirements_in_group,
                is_inferred,
            )

            merged.append(
                requirements_in_group[0].model_copy(
                    update={
                        "statement": max(
                            (requirement.statement for requirement in requirements_in_group),
                            key=len,
                        ),
                        "source_document_id": sorted(
                            {
                                requirement.source_document_id
                                for requirement in requirements_in_group
                            }
                        )[0],
                        "source_excerpt": source_excerpts[0] if source_excerpts else "",
                        "ambiguities": sorted(
                            {
                                ambiguity
                                for requirement in requirements_in_group
                                for ambiguity in requirement.ambiguities
                            }
                        ),
                        "confidence": self._lowest_confidence(requirements_in_group),
                        "is_inferred": is_inferred,
                        "inference_reasoning": reasoning,
                    }
                )
            )

        return merged

    def _delete_collection(self, collection_name: str) -> None:
        """Delete the temporary collection, logging failures without masking results."""
        try:
            self.qdrant.delete_collection(collection_name)
        except Exception as exc:
            logger.warning(
                "consolidation: failed to delete temporary collection=%s error=%s",
                collection_name,
                str(exc),
            )

    @staticmethod
    def _collection_name(session_id: str) -> str:
        """Build a Qdrant-safe temporary collection name."""
        return f"specweaver_session_{session_id}".replace("-", "_")

    @staticmethod
    def _lowest_confidence(
        requirements: list[ExtractedRequirement],
    ) -> ConfidenceLevel:
        """Return the least confident label from a requirement group."""
        confidence_order = [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
            ConfidenceLevel.INFERRED,
        ]
        return max(
            (requirement.confidence for requirement in requirements),
            key=lambda confidence: confidence_order.index(confidence),
        )

    @staticmethod
    def _combine_inference_reasoning(
        requirements: list[ExtractedRequirement],
        is_inferred: bool,
    ) -> str | None:
        """Combine inference reasoning only when a merged group is inferred."""
        if not is_inferred:
            return None

        reasonings = [
            requirement.inference_reasoning
            for requirement in requirements
            if requirement.inference_reasoning
        ]
        return " | ".join(reasonings) if reasonings else None

    @staticmethod
    def _enum_value(value) -> str:
        """Return the serialized value for enums or already-normalized strings."""
        return str(getattr(value, "value", value))
