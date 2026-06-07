"""Qdrant-backed vector memory for architecture pattern storage and retrieval."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

import openai
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

# Namespace UUID for deterministic conversation-id-based point IDs
_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class MemoryStore:
    """Stores and retrieves architecture designs using Qdrant vector search."""

    COLLECTION_NAME = "architecture_patterns"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536

    def __init__(self) -> None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self._qdrant = QdrantClient(url=qdrant_url)
        self._openai = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    async def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not exist."""
        try:
            collections = self._qdrant.get_collections().collections
            names = [c.name for c in collections]
            if self.COLLECTION_NAME not in names:
                self._qdrant.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
            logger.info("Qdrant collection ready")
        except Exception:
            logger.warning(
                "Failed to ensure Qdrant collection — Qdrant may be unavailable",
                exc_info=True,
            )

    async def _embed(self, text: str) -> list[float]:
        """Embed text using OpenAI text-embedding-3-small."""
        response = await self._openai.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding

    async def store_design(
        self,
        conversation_id: str,
        requirements: str,
        architecture_design: dict,
        characteristics: list[dict],
    ) -> None:
        """Store an architecture design as a vector in Qdrant.

        Args:
            conversation_id: The conversation that produced this design.
            requirements: The raw requirements text (used as embedding input).
            architecture_design: The full architecture design dict.
            characteristics: The inferred characteristics list.
        """
        try:
            embedding = await self._embed(requirements)
            point_id = str(uuid.uuid5(_NAMESPACE, conversation_id))
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "conversation_id": conversation_id,
                    "domain": architecture_design.get("domain", ""),
                    "system_type": architecture_design.get("system_type", ""),
                    "architecture_style": architecture_design.get("style", ""),
                    "characteristic_names": [
                        c.get("name") for c in characteristics
                    ],
                    "stored_at": datetime.utcnow().isoformat(),
                },
            )
            self._qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[point],
            )
            logger.debug("Stored design for conversation %s", conversation_id)
        except Exception:
            logger.warning(
                "Failed to store design in Qdrant for conversation %s",
                conversation_id,
                exc_info=True,
            )

    async def retrieve_similar(
        self,
        requirements: str,
        limit: int = 3,
    ) -> list[dict]:
        """Retrieve similar past architecture designs.

        Args:
            requirements: The requirements text to search by.
            limit: Maximum number of results to return.

        Returns:
            List of payload dicts from similar designs. Empty list on failure.
        """
        try:
            embedding = await self._embed(requirements)
            response = self._qdrant.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embedding,
                limit=limit,
                with_payload=True,
            )
            return [hit.payload for hit in response.points if hit.payload]
        except Exception:
            logger.warning(
                "Failed to retrieve similar designs from Qdrant",
                exc_info=True,
            )
            return []
