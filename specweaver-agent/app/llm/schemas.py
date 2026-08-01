"""JSON schemas for structured LLM output by SpecWeaver stage."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel

from app.models.contracts import (
    ArchInputPackage,
    ClassifiedRequirementSet,
    ExtractionResult,
)


class GapAnalysisLLMItem(BaseModel):
    """Single gap item returned by the gap analysis prompt."""

    area: str
    severity: str
    explanation: str
    clarification_question: str
    affected_categories: list[str]


class GapAnalysisLLMResult(BaseModel):
    """LLM-only gap analysis payload before deterministic IDs are added."""

    gaps: list[GapAnalysisLLMItem]


class ConflictDetectionLLMItem(BaseModel):
    """Single conflict item returned by the conflict detection prompt."""

    requirement_ids: list[str]
    description: str
    interpretations: list[str]
    clarification_question: str


class ConflictDetectionLLMResult(BaseModel):
    """LLM-only conflict payload before deterministic IDs are added."""

    conflicts: list[ConflictDetectionLLMItem]


def _enforce_openai_object_schema(node: Any) -> Any:
    """
    Ensure OpenAI strict JSON schema compatibility for object nodes.

    OpenAI's strict `response_format` requires every JSON schema object node to
    explicitly declare `additionalProperties`. Pydantic omits this on many
    generated object nodes by default, which causes OpenAI to reject the schema.

    Args:
        node: JSON-schema fragment (dict, list, or scalar).
    Returns:
        Schema fragment with missing object `additionalProperties` fields added.
    """
    if isinstance(node, dict):
        if node.get("type") == "object" and "additionalProperties" not in node:
            node["additionalProperties"] = False

        properties = node.get("properties")
        if isinstance(properties, dict) and properties:
            required = node.get("required")
            required_list = required if isinstance(required, list) else []

            # OpenAI strict response_format requires object `required` to list
            # every key present in `properties`, even for nullable/optional fields.
            missing_keys = [key for key in properties.keys() if key not in required_list]
            if missing_keys:
                node["required"] = [*required_list, *missing_keys]

        for key in ("properties", "$defs", "definitions", "patternProperties"):
            branch = node.get(key)
            if isinstance(branch, dict):
                for child in branch.values():
                    _enforce_openai_object_schema(child)

        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            branch = node.get(key)
            if isinstance(branch, list):
                for child in branch:
                    _enforce_openai_object_schema(child)

        for key in ("items", "contains", "if", "then", "else", "not"):
            if key in node:
                _enforce_openai_object_schema(node[key])

        additional_properties = node.get("additionalProperties")
        if isinstance(additional_properties, dict):
            _enforce_openai_object_schema(additional_properties)

        return node

    if isinstance(node, list):
        for child in node:
            _enforce_openai_object_schema(child)
    return node


def _schema_for_openai_strict(model: type) -> dict[str, Any]:
    """
    Build a Pydantic schema compatible with OpenAI strict response_format.

    Args:
        model: Pydantic model class used for structured output.
    Returns:
        JSON schema with explicit object `additionalProperties` declarations.
    """
    raw_schema = deepcopy(model.model_json_schema(by_alias=False))
    return _enforce_openai_object_schema(raw_schema)

SCHEMAS = {
    "extraction": _schema_for_openai_strict(ExtractionResult),
    "classification": _schema_for_openai_strict(ClassifiedRequirementSet),
    "gap_analysis": _schema_for_openai_strict(GapAnalysisLLMResult),
    "conflict_detection": _schema_for_openai_strict(ConflictDetectionLLMResult),
    "output_formatting": _schema_for_openai_strict(ArchInputPackage),
}
