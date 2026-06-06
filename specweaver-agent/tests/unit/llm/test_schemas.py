"""Tests for OpenAI strict-compatible JSON schemas."""

from __future__ import annotations

from typing import Any

from app.llm.schemas import SCHEMAS


def _collect_object_nodes_missing_additional_properties(
    node: Any,
    path: str = "$",
) -> list[str]:
    """
    Return paths for object schema nodes missing additionalProperties.

    Args:
        node: JSON-schema fragment.
        path: Logical path used for assertion diagnostics.
    Returns:
        List of schema paths where object nodes are incomplete.
    """
    missing: list[str] = []

    if isinstance(node, dict):
        if node.get("type") == "object" and "additionalProperties" not in node:
            missing.append(path)

        for key, value in node.items():
            if isinstance(value, dict):
                missing.extend(
                    _collect_object_nodes_missing_additional_properties(
                        value,
                        f"{path}.{key}",
                    )
                )
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    missing.extend(
                        _collect_object_nodes_missing_additional_properties(
                            child,
                            f"{path}.{key}[{index}]",
                        )
                    )

    elif isinstance(node, list):
        for index, child in enumerate(node):
            missing.extend(
                _collect_object_nodes_missing_additional_properties(
                    child,
                    f"{path}[{index}]",
                )
            )

    return missing


def _collect_object_nodes_missing_required_property_keys(
    node: Any,
    path: str = "$",
) -> list[str]:
    """
    Return paths for object schema nodes where required misses property keys.

    Args:
        node: JSON-schema fragment.
        path: Logical path used for assertion diagnostics.
    Returns:
        List of schema paths where required does not include every property key.
    """
    missing: list[str] = []

    if isinstance(node, dict):
        if node.get("type") == "object" and isinstance(node.get("properties"), dict):
            properties = node["properties"]
            required = node.get("required")
            required_set = set(required) if isinstance(required, list) else set()
            property_set = set(properties.keys())
            if not property_set.issubset(required_set):
                missing_keys = sorted(property_set - required_set)
                missing.append(f"{path} missing required: {', '.join(missing_keys)}")

        for key, value in node.items():
            if isinstance(value, dict):
                missing.extend(
                    _collect_object_nodes_missing_required_property_keys(
                        value,
                        f"{path}.{key}",
                    )
                )
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    missing.extend(
                        _collect_object_nodes_missing_required_property_keys(
                            child,
                            f"{path}.{key}[{index}]",
                        )
                    )

    elif isinstance(node, list):
        for index, child in enumerate(node):
            missing.extend(
                _collect_object_nodes_missing_required_property_keys(
                    child,
                    f"{path}[{index}]",
                )
            )

    return missing


def test_extraction_schema_declares_additional_properties_for_all_object_nodes():
    schema = SCHEMAS["extraction"]
    missing_paths = _collect_object_nodes_missing_additional_properties(schema)

    assert not missing_paths, (
        "Extraction schema has object nodes missing additionalProperties: "
        + ", ".join(missing_paths)
    )


def test_extraction_schema_root_forbids_unexpected_fields():
    schema = SCHEMAS["extraction"]
    assert schema.get("additionalProperties") is False


def test_extraction_schema_required_lists_all_properties_for_object_nodes():
    schema = SCHEMAS["extraction"]
    missing_paths = _collect_object_nodes_missing_required_property_keys(schema)

    assert not missing_paths, (
        "Extraction schema has object nodes with incomplete required arrays: "
        + ", ".join(missing_paths)
    )
