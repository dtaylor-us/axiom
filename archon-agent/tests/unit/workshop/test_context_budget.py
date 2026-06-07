"""Unit tests for app.workshop.context_manager."""

from __future__ import annotations

import uuid

import pytest

from app.workshop.context import WorkshopContext
from app.workshop.context_manager import (
    MAX_CONTEXT_TOKENS,
    MAX_RAW_INPUT_CHARS,
    MAX_SINGLE_INPUT_CHARS,
    MAX_TURNS_IN_FULL,
    estimate_context_size,
    prepare_context_for_prompt,
    validate_input_size,
)


def _make_context(**kwargs) -> WorkshopContext:
    defaults = dict(
        session_id=str(uuid.uuid4()),
        user_id="test-user",
        system_name="TestSystem",
        current_turn=1,
    )
    defaults.update(kwargs)
    return WorkshopContext(**defaults)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_max_context_tokens_constant():
    assert MAX_CONTEXT_TOKENS == 60_000


def test_max_raw_input_chars_constant():
    assert MAX_RAW_INPUT_CHARS == 20_000


def test_max_turns_in_full_constant():
    assert MAX_TURNS_IN_FULL == 5


def test_max_single_input_chars_constant():
    assert MAX_SINGLE_INPUT_CHARS == 3_000


# ---------------------------------------------------------------------------
# estimate_context_size
# ---------------------------------------------------------------------------

def test_estimate_context_size_empty_context():
    ctx = _make_context()
    size = estimate_context_size(ctx)
    assert size >= 0


def test_estimate_grows_with_input():
    ctx_small = _make_context(raw_inputs=["short"])
    ctx_large = _make_context(raw_inputs=["a" * 10_000])
    assert estimate_context_size(ctx_large) > estimate_context_size(ctx_small)


# ---------------------------------------------------------------------------
# prepare_context_for_prompt
# ---------------------------------------------------------------------------

def test_prepare_context_returns_dict():
    ctx = _make_context()
    result = prepare_context_for_prompt(ctx)
    assert isinstance(result, dict)
    assert "session_id" in result
    assert "workshop_phase" in result


def test_prepare_context_uses_summarised_when_large():
    """When context is huge, summarised view is returned (no error raised)."""
    # Fill raw_inputs with very large strings to exceed budget
    big_inputs = ["x" * 5_000] * 100
    ctx = _make_context(raw_inputs=big_inputs)
    result = prepare_context_for_prompt(ctx)
    # Should still return a valid dict
    assert isinstance(result, dict)
    assert "session_id" in result


# ---------------------------------------------------------------------------
# validate_input_size
# ---------------------------------------------------------------------------

def test_validate_input_size_short_input_ok():
    ok, msg = validate_input_size("short input")
    assert ok is False
    assert msg == ""


def test_validate_input_size_long_input_warns():
    long_input = "a" * (MAX_SINGLE_INPUT_CHARS + 1)
    is_oversized, msg = validate_input_size(long_input)
    assert is_oversized is True
    assert len(msg) > 0


def test_validate_input_size_exactly_at_limit_is_ok():
    exactly = "a" * MAX_SINGLE_INPUT_CHARS
    is_oversized, _ = validate_input_size(exactly)
    assert is_oversized is False
