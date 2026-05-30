from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.memory.store import MemoryStore


class TestMemoryStore:
    """Tests for MemoryStore — Qdrant-backed vector memory."""

    @pytest.fixture
    def mock_qdrant(self):
        """Return a mock QdrantClient."""
        client = MagicMock()
        # get_collections returns empty list by default
        collections_response = MagicMock()
        collections_response.collections = []
        client.get_collections.return_value = collections_response
        return client

    @pytest.fixture
    def mock_openai(self):
        """Return a mock AsyncOpenAI client."""
        client = AsyncMock()
        embedding_data = MagicMock()
        embedding_data.embedding = [0.1] * 1536
        response = MagicMock()
        response.data = [embedding_data]
        client.embeddings.create = AsyncMock(return_value=response)
        return client

    @pytest.fixture
    def store(self, mock_qdrant, mock_openai):
        """Return a MemoryStore with mocked dependencies."""
        s = MemoryStore.__new__(MemoryStore)
        s._qdrant = mock_qdrant
        s._openai = mock_openai
        return s

    async def test_ensure_collection_creates_when_missing(
        self, store, mock_qdrant,
    ):
        """_ensure_collection() creates the collection when it doesn't exist."""
        await store._ensure_collection()

        mock_qdrant.create_collection.assert_called_once()
        call_kwargs = mock_qdrant.create_collection.call_args
        assert call_kwargs[1]["collection_name"] == "architecture_patterns"

    async def test_ensure_collection_skips_when_exists(
        self, store, mock_qdrant,
    ):
        """_ensure_collection() does not create if collection already exists."""
        existing = MagicMock()
        existing.name = "architecture_patterns"
        collections = MagicMock()
        collections.collections = [existing]
        mock_qdrant.get_collections.return_value = collections

        await store._ensure_collection()

        mock_qdrant.create_collection.assert_not_called()

    async def test_ensure_collection_does_not_raise_on_error(
        self, store, mock_qdrant,
    ):
        """_ensure_collection() logs warning but does not raise on failure."""
        mock_qdrant.get_collections.side_effect = Exception("connection refused")

        # Should not raise
        await store._ensure_collection()

    async def test_store_design_upserts(
        self, store, mock_qdrant, mock_openai,
    ):
        """store_design() embeds and upserts a point to Qdrant."""
        await store.store_design(
            conversation_id="conv-1",
            requirements="Build a payment system",
            architecture_design={"style": "microservices", "domain": "fintech"},
            characteristics=[{"name": "scalability"}],
        )

        mock_openai.embeddings.create.assert_awaited_once()
        mock_qdrant.upsert.assert_called_once()

    async def test_store_design_does_not_raise_on_error(
        self, store, mock_qdrant, mock_openai,
    ):
        """store_design() catches exceptions and does not raise."""
        mock_openai.embeddings.create.side_effect = Exception("api error")

        # Should not raise
        await store.store_design(
            conversation_id="conv-1",
            requirements="test",
            architecture_design={},
            characteristics=[],
        )

    async def test_retrieve_similar_returns_payloads(
        self, store, mock_qdrant, mock_openai,
    ):
        """retrieve_similar() returns list of payload dicts."""
        hit1 = MagicMock()
        hit1.payload = {"conversation_id": "past-1", "domain": "fintech"}
        hit2 = MagicMock()
        hit2.payload = {"conversation_id": "past-2", "domain": "healthcare"}
        mock_qdrant.query_points.return_value = MagicMock(points=[hit1, hit2])

        results = await store.retrieve_similar("Build a payment system")

        assert len(results) == 2
        assert results[0]["domain"] == "fintech"

    async def test_retrieve_similar_returns_empty_on_error(
        self, store, mock_qdrant, mock_openai,
    ):
        """retrieve_similar() returns [] on failure."""
        mock_openai.embeddings.create.side_effect = Exception("api error")

        results = await store.retrieve_similar("test")

        assert results == []

    async def test_retrieve_similar_filters_none_payloads(
        self, store, mock_qdrant, mock_openai,
    ):
        """retrieve_similar() filters out hits with None payloads."""
        hit1 = MagicMock()
        hit1.payload = {"domain": "fintech"}
        hit2 = MagicMock()
        hit2.payload = None
        mock_qdrant.query_points.return_value = MagicMock(points=[hit1, hit2])

        results = await store.retrieve_similar("test")

        assert len(results) == 1
