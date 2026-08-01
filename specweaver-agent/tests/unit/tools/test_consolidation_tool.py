"""Tests for the Phase 1b consolidation tool."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.contracts import (
    ConfidenceLevel,
    ConsolidationGroup,
    ConsolidationResult,
    ExtractionResult,
)
from app.tools.consolidation_tool import ConsolidationTool


def _tool() -> ConsolidationTool:
    """Create a consolidation tool without opening a Qdrant connection."""
    tool = ConsolidationTool.__new__(ConsolidationTool)
    tool.llm_client = MagicMock()
    tool.qdrant = MagicMock()
    return tool


def _query_response(*point_ids_and_scores: tuple[int, float]) -> SimpleNamespace:
    """Build a Qdrant query_points-style response for unit tests."""
    return SimpleNamespace(
        points=[
            SimpleNamespace(id=point_id, score=score)
            for point_id, score in point_ids_and_scores
        ]
    )


def _group(requirements, is_duplicate_group: bool = True) -> ConsolidationGroup:
    """Build a representative consolidation group."""
    return ConsolidationGroup(
        group_id="group-1",
        requirements=requirements,
        similarity_score=0.95,
        is_duplicate_group=is_duplicate_group,
    )


def test_merge_groups_merges_duplicate_requirements(extracted_requirement):
    """Duplicate groups should collapse to one requirement."""
    duplicate = extracted_requirement.model_copy(
        update={
            "requirement_id": "REQ-2",
            "statement": "The system shall support enterprise single sign-on.",
            "source_document_id": "doc-2",
            "source_excerpt": "support enterprise single sign-on",
        }
    )

    result = _tool()._merge_groups(
        [_group([extracted_requirement, duplicate])],
        [extracted_requirement, duplicate],
    )

    assert len(result) == 1


def test_merge_groups_uses_lowest_confidence_from_group(extracted_requirement):
    """Merged requirements should retain the least confident source label."""
    duplicate = extracted_requirement.model_copy(
        update={"requirement_id": "REQ-2", "confidence": ConfidenceLevel.LOW}
    )

    result = _tool()._merge_groups(
        [_group([extracted_requirement, duplicate])],
        [extracted_requirement, duplicate],
    )

    assert result[0].confidence == ConfidenceLevel.LOW


def test_merge_groups_sets_inferred_when_any_requirement_is_inferred(
    extracted_requirement,
):
    """Merged requirements should be inferred when any source was inferred."""
    duplicate = extracted_requirement.model_copy(
        update={
            "requirement_id": "REQ-2",
            "is_inferred": True,
            "inference_reasoning": "Implied by enterprise login needs.",
        }
    )

    result = _tool()._merge_groups(
        [_group([extracted_requirement, duplicate])],
        [extracted_requirement, duplicate],
    )

    assert result[0].is_inferred is True


def test_merge_groups_combines_all_ambiguities(extracted_requirement):
    """Merged requirements should preserve unique ambiguities from all sources."""
    first = extracted_requirement.model_copy(update={"ambiguities": ["scope unclear"]})
    duplicate = extracted_requirement.model_copy(
        update={"requirement_id": "REQ-2", "ambiguities": ["idp unclear"]}
    )

    result = _tool()._merge_groups([_group([first, duplicate])], [first, duplicate])

    assert result[0].ambiguities == ["idp unclear", "scope unclear"]


def test_merge_groups_passes_non_duplicate_groups_through(extracted_requirement):
    """Non-duplicate groups should be returned unchanged."""
    result = _tool()._merge_groups(
        [_group([extracted_requirement], is_duplicate_group=False)],
        [extracted_requirement],
    )

    assert result == [extracted_requirement]


@pytest.mark.asyncio
async def test_run_deletes_collection_when_consolidation_raises(
    context,
    extraction_result,
    monkeypatch,
):
    """Temporary Qdrant collections must be deleted even on failure."""
    context.extraction_results = [extraction_result]
    tool = _tool()
    delete_collection = MagicMock()

    async def raise_error(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(tool, "_consolidate", raise_error)
    monkeypatch.setattr(tool, "_delete_collection", delete_collection)

    with pytest.raises(RuntimeError):
        await tool.run(context)

    delete_collection.assert_called_once_with("specweaver_session_session_1")


@pytest.mark.asyncio
async def test_run_logs_warning_when_no_requirements(context, caplog):
    """An empty extraction set should be recorded as a completed stage."""
    tool = _tool()

    result = await tool.run(context)

    assert "no requirements to consolidate" in caplog.text
    assert "consolidation" in result.completed_stages


@pytest.mark.asyncio
async def test_run_appends_consolidation_to_completed_stages(
    context,
    extraction_result,
    extracted_requirement,
    monkeypatch,
):
    """Successful consolidation should update context and stage history."""
    context.extraction_results = [extraction_result]
    tool = _tool()

    async def consolidate(*args):
        return ConsolidationResult(
            session_id="session-1",
            consolidated_groups=[_group([extracted_requirement], False)],
            merged_requirements=[extracted_requirement],
            duplicate_count=0,
            original_count=1,
            consolidated_count=1,
        )

    monkeypatch.setattr(tool, "_consolidate", consolidate)
    monkeypatch.setattr(tool, "_delete_collection", MagicMock())

    result = await tool.run(context)

    assert "consolidation" in result.completed_stages
    assert isinstance(result.extraction_results[0], ExtractionResult)


@pytest.mark.asyncio
async def test_embed_requirements_uses_openai_when_provider_is_openai(
    extracted_requirement,
    monkeypatch,
):
    """OpenAI deployments should not route embeddings through Ollama."""
    tool = _tool()
    create_embeddings = AsyncMock(
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2, 0.3]),
                SimpleNamespace(embedding=[0.4, 0.5, 0.6]),
            ]
        )
    )
    fake_client = SimpleNamespace(
        embeddings=SimpleNamespace(create=create_embeddings)
    )

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setattr(
        "app.tools.consolidation_tool.openai.AsyncOpenAI",
        lambda api_key: fake_client,
    )

    duplicate = extracted_requirement.model_copy(
        update={
            "requirement_id": "REQ-2",
            "statement": "The system shall support SSO for enterprise tenants.",
        }
    )

    embeddings = await tool._embed_requirements([extracted_requirement, duplicate])

    assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    create_embeddings.assert_awaited_once_with(
        model="text-embedding-3-small",
        input=[
            extracted_requirement.statement,
            "The system shall support SSO for enterprise tenants.",
        ],
    )


@pytest.mark.asyncio
async def test_consolidate_creates_collection_with_embedding_dimension(
    extracted_requirement,
    monkeypatch,
):
    """Qdrant collections should match the active embedding vector size."""
    tool = _tool()
    create_collection = MagicMock()

    monkeypatch.setattr(
        tool,
        "_embed_requirements",
        AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4]]),
    )
    monkeypatch.setattr(tool, "_create_collection", create_collection)
    monkeypatch.setattr(tool, "_store_embeddings", MagicMock())
    monkeypatch.setattr(tool, "_find_duplicate_groups", MagicMock(return_value=[]))
    monkeypatch.setattr(
        tool,
        "_merge_groups",
        MagicMock(return_value=[extracted_requirement]),
    )

    await tool._consolidate("session-1", [extracted_requirement], "collection-1")

    create_collection.assert_called_once_with("collection-1", 4)


def test_find_duplicate_groups_uses_qdrant_query_points(extracted_requirement):
    """Duplicate grouping should work with the installed Qdrant client response shape."""
    tool = _tool()
    duplicate = extracted_requirement.model_copy(
        update={
            "requirement_id": "REQ-2",
            "statement": "The platform shall support secure user login.",
        }
    )
    tool.qdrant.query_points.return_value = _query_response((0, 1.0), (1, 0.96))

    groups = tool._find_duplicate_groups(
        "collection-1",
        [extracted_requirement, duplicate],
        [[0.1, 0.2], [0.2, 0.3]],
    )

    assert len(groups) == 1
    assert groups[0].is_duplicate_group is True
    assert len(groups[0].requirements) == 2
