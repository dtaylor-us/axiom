"""Unit tests for LLM context budgeting helpers."""

from __future__ import annotations

import logging

from app.llm.budget import budget_json_list, budget_string, get_input_budget


def test_budget_json_list_returns_full_list_when_under_budget() -> None:
    """Small JSON lists are returned unchanged."""
    items = [{"id": "a"}, {"id": "b"}]

    result = budget_json_list(items, max_tokens=100)

    assert result == items


def test_budget_json_list_truncates_list_when_over_budget() -> None:
    """Oversized JSON lists are truncated to fit."""
    items = [{"id": str(i), "text": "x" * 50} for i in range(5)]

    result = budget_json_list(items, max_tokens=30)

    assert len(result) < len(items)


def test_budget_json_list_logs_warning_when_truncating(caplog) -> None:
    """Truncation emits a warning with stage context."""
    items = [{"id": str(i), "text": "x" * 50} for i in range(5)]

    with caplog.at_level(logging.WARNING, logger="app.llm.budget"):
        budget_json_list(items, max_tokens=20, stage_name="stage")

    assert any("BUDGET: truncated" in record.message for record in caplog.records)


def test_budget_json_list_preserves_items_from_start() -> None:
    """List budgeting keeps the earliest items first."""
    items = [{"id": str(i), "text": "x" * 50} for i in range(5)]

    result = budget_json_list(items, max_tokens=30)

    assert result[0]["id"] == "0"


def test_budget_string_returns_full_string_when_under_budget() -> None:
    """Small strings are returned unchanged."""
    text = "short text"

    result = budget_string(text, max_tokens=10)

    assert result == text


def test_budget_string_truncates_and_adds_notice_when_over_budget() -> None:
    """Oversized strings include a truncation notice."""
    text = "x" * 100

    result = budget_string(text, max_tokens=10)

    assert result.endswith("[... truncated to fit context budget ...]")
    assert len(result) < len(text) + len(result)


def test_get_input_budget_returns_smaller_budget_for_large_output_stages() -> None:
    """Large-output stages reserve more context for generation."""
    standard_budget = get_input_budget("requirement_parsing", "ollama", 10000)
    large_budget = get_input_budget("architecture_generation", "ollama", 10000)

    assert large_budget < standard_budget


def test_get_input_budget_returns_large_budget_for_openai_provider() -> None:
    """OpenAI receives the large practical budget."""
    budget = get_input_budget("architecture_generation", "openai", 10000)

    assert budget == 64000
