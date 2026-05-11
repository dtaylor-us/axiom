"""Tests for app.llm.schemas — the schema registry.

Covers ADL-034: SCHEMAS completeness, correctness, and absence of top-level title.
"""
from __future__ import annotations

import pytest

from app.llm.schemas import SCHEMAS


EXPECTED_STAGE_KEYS = {
    "requirement_parsing",
    "requirement_challenge",
    "scenario_modeling",
    "characteristic_inference",
    "tactics_recommendation",
    "conflict_analysis",
    "architecture_generation",
    "buy_vs_build_analysis",
    "trade_off_analysis",
    "adl_generation",
    "weakness_analysis",
    "fmea_analysis",
    "diagram_generation_single",
}


class TestSchemaRegistryCompleteness:
    """SCHEMAS dict must contain all expected stage keys."""

    def test_all_expected_keys_present(self):
        missing = EXPECTED_STAGE_KEYS - set(SCHEMAS.keys())
        assert not missing, f"Missing schema keys: {missing}"

    def test_no_unexpected_keys(self):
        extra = set(SCHEMAS.keys()) - EXPECTED_STAGE_KEYS
        assert not extra, f"Unexpected schema keys (update EXPECTED_STAGE_KEYS if intentional): {extra}"

    def test_minimum_key_count(self):
        assert len(SCHEMAS) >= 8, "SCHEMAS must contain at least 8 entries (sanity assertion)"

    @pytest.mark.parametrize("key", sorted(EXPECTED_STAGE_KEYS))
    def test_each_schema_is_dict(self, key):
        assert isinstance(SCHEMAS[key], dict), f"Schema for '{key}' must be a dict"

    @pytest.mark.parametrize("key", sorted(EXPECTED_STAGE_KEYS))
    def test_each_schema_has_type_or_properties(self, key):
        schema = SCHEMAS[key]
        has_type = "type" in schema
        has_properties = "properties" in schema
        has_defs = "$defs" in schema or "definitions" in schema
        assert has_type or has_properties or has_defs, (
            f"Schema for '{key}' must have 'type', 'properties', or '$defs'. Got: {list(schema.keys())}"
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STAGE_KEYS))
    def test_no_top_level_title(self, key):
        """Top-level 'title' must be stripped — OpenAI rejects it in strict mode."""
        assert "title" not in SCHEMAS[key], (
            f"Schema for '{key}' must not have top-level 'title' key. "
            "Strip it via the _schema() helper."
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STAGE_KEYS))
    def test_schema_is_not_empty(self, key):
        assert len(SCHEMAS[key]) > 0, f"Schema for '{key}' is empty"
