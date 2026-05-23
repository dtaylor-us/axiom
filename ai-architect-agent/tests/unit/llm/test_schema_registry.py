"""Tests for app.llm.schemas — the schema registry.

Covers ADL-034: SCHEMAS completeness, correctness, and absence of top-level title.

Design note: SCHEMAS only contains schemas that pass OpenAI strict-mode
compatibility (no freeform dict/list[dict] fields). Schemas that contain
freeform fields are tracked in _ALL_SCHEMAS but excluded from SCHEMAS so
that LLMClient uses json_object mode directly, avoiding an expensive 400
rejection roundtrip. Tests verify both the full tracking set and the strict
subset independently.
"""
from __future__ import annotations

import pytest

from app.llm.schemas import SCHEMAS, _ALL_SCHEMAS, _has_freeform_object


# All stage/tool keys that must be tracked in _ALL_SCHEMAS, regardless of
# whether they are strict-compatible or not.
ALL_EXPECTED_STAGE_KEYS = {
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

# Keys known to be strict-compatible (must appear in SCHEMAS).
EXPECTED_STRICT_KEYS = {
    "diagram_generation_single",
}

# Keys known to contain freeform dict fields (must NOT appear in SCHEMAS).
EXPECTED_JSON_OBJECT_KEYS = ALL_EXPECTED_STAGE_KEYS - EXPECTED_STRICT_KEYS


class TestSchemaRegistryTracking:
    """_ALL_SCHEMAS must track every pipeline stage, compatible or not."""

    def test_all_expected_keys_tracked(self):
        missing = ALL_EXPECTED_STAGE_KEYS - set(_ALL_SCHEMAS.keys())
        assert not missing, f"Missing keys in _ALL_SCHEMAS: {missing}"

    def test_no_unexpected_keys_tracked(self):
        extra = set(_ALL_SCHEMAS.keys()) - ALL_EXPECTED_STAGE_KEYS
        assert not extra, (
            f"Unexpected keys in _ALL_SCHEMAS (update ALL_EXPECTED_STAGE_KEYS if intentional): {extra}"
        )

    def test_strict_schemas_are_dicts(self):
        """Strict-compatible entries must be non-None dicts."""
        for key in EXPECTED_STRICT_KEYS:
            assert isinstance(_ALL_SCHEMAS.get(key), dict), (
                f"_ALL_SCHEMAS['{key}'] should be a dict (strict-compatible)"
            )

    def test_json_object_schemas_are_none(self):
        """Freeform-dict entries must be None (excluded from strict registry)."""
        for key in EXPECTED_JSON_OBJECT_KEYS:
            assert _ALL_SCHEMAS.get(key) is None, (
                f"_ALL_SCHEMAS['{key}'] should be None (freeform dict fields make it "
                "strict-incompatible). If the model was updated to remove freeform fields, "
                "move this key from EXPECTED_JSON_OBJECT_KEYS to EXPECTED_STRICT_KEYS."
            )


class TestStrictSchemaRegistry:
    """SCHEMAS must contain only strict-compatible schemas, correctly formed."""

    def test_strict_keys_present(self):
        missing = EXPECTED_STRICT_KEYS - set(SCHEMAS.keys())
        assert not missing, f"Expected strict schemas not found in SCHEMAS: {missing}"

    def test_no_json_object_keys_in_strict_registry(self):
        leaked = EXPECTED_JSON_OBJECT_KEYS & set(SCHEMAS.keys())
        assert not leaked, (
            f"Freeform-dict schemas leaked into strict SCHEMAS: {leaked}. "
            "These would cause OpenAI 400 rejections on every pipeline call."
        )

    def test_no_additional_unexpected_keys(self):
        extra = set(SCHEMAS.keys()) - ALL_EXPECTED_STAGE_KEYS
        assert not extra, f"Unexpected keys in SCHEMAS: {extra}"

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_each_strict_schema_is_dict(self, key):
        assert isinstance(SCHEMAS.get(key), dict), f"Schema for '{key}' must be a dict"

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_each_strict_schema_has_type_or_properties(self, key):
        schema = SCHEMAS[key]
        has_type = "type" in schema
        has_properties = "properties" in schema
        has_defs = "$defs" in schema or "definitions" in schema
        assert has_type or has_properties or has_defs, (
            f"Schema for '{key}' must have 'type', 'properties', or '$defs'. Got: {list(schema.keys())}"
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_no_top_level_title(self, key):
        """Top-level 'title' must be stripped — OpenAI rejects it in strict mode."""
        assert "title" not in SCHEMAS[key], (
            f"Schema for '{key}' must not have top-level 'title' key. "
            "Strip it via the _strict_schema() helper."
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_schema_is_not_empty(self, key):
        assert len(SCHEMAS[key]) > 0, f"Schema for '{key}' is empty"

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_no_freeform_object_nodes(self, key):
        """Every schema in the strict registry must have no freeform dict nodes.

        A freeform node (additionalProperties: true) causes OpenAI to reject
        the schema with a 400, triggering an expensive fallback roundtrip.
        """
        schema = SCHEMAS[key]
        assert not _has_freeform_object(schema), (
            f"Schema '{key}' contains a freeform object node (additionalProperties: true). "
            "This will cause a 400 rejection from OpenAI strict mode. "
            "Either define the dict fields with proper Pydantic models, or move "
            "this key to EXPECTED_JSON_OBJECT_KEYS so it uses json_object mode."
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_top_level_has_additional_properties_false(self, key):
        """Every top-level object schema must declare additionalProperties: false."""
        schema = SCHEMAS[key]
        if schema.get("type") == "object" or "properties" in schema:
            assert schema.get("additionalProperties") is False, (
                f"Schema '{key}' is missing 'additionalProperties: false'. "
                "Run _make_openai_strict() on the schema to fix."
            )

    @pytest.mark.parametrize("key", sorted(EXPECTED_STRICT_KEYS))
    def test_top_level_required_covers_all_properties(self, key):
        """When properties exist, every key must appear in required."""
        schema = SCHEMAS[key]
        props = schema.get("properties", {})
        if not props:
            return
        required = set(schema.get("required", []))
        missing = set(props.keys()) - required
        assert not missing, (
            f"Schema '{key}' has properties not listed in required: {missing}. "
            "Run _make_openai_strict() on the schema to fix."
        )
