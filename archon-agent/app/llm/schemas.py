"""JSON schema registry for all pipeline stage outputs.

Each entry is derived from the corresponding Pydantic output model in
app.models.outputs using model.model_json_schema(). Schemas are computed
once at import time and cached as module-level constants.

Only schemas that are fully compatible with OpenAI's strict mode are
included in this registry. A schema is compatible when every object node
in the tree declares ``additionalProperties: false`` — which requires
every dict-typed field to have a fully-specified structure. Models that
use ``list[dict]`` or bare ``dict`` fields (freeform) are auto-excluded
at import time and receive ``None`` from ``SCHEMAS.get()``, which causes
``LLMClient.complete()`` to use json_object mode directly (no rejection
roundtrip).

Usage:
    from app.llm.schemas import SCHEMAS

    raw = await llm_client.complete(
        prompt,
        output_schema=SCHEMAS.get("requirement_parsing"),  # None → json_object
        schema_name="requirement_parsing",
    )
"""

from __future__ import annotations

import logging

from app.models.outputs import (
    ParsedRequirements,
    ChallengeOutput,
    ScenarioOutput,
    CharacteristicOutput,
    TacticsOutput,
    ConflictOutput,
    ArchitectureDesign,
    BuyVsBuildOutput,
    TradeOffOutput,
    ADLOutput,
    WeaknessOutput,
    FMEAOutput,
    SingleDiagramOutput,
)

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema derivation helpers
# ---------------------------------------------------------------------------

def _make_openai_strict(schema: dict) -> dict:
    """Recursively adapt a Pydantic JSON schema for OpenAI strict mode.

    OpenAI's json_schema strict enforcement requires every object-type node
    in the schema to have:
      - ``additionalProperties: false``  (no extra keys allowed)
      - ``required`` listing every declared property key

    Pydantic's ``model_json_schema()`` omits both whenever all model fields
    carry default values (which is the case for every output model here).
    This function applies those constraints to every object node that has
    declared properties. Freeform object nodes (no ``properties`` key, like
    the items of ``list[dict]``) are left unchanged because setting
    ``additionalProperties: false`` with no declared properties would produce
    a schema that only accepts an empty object ``{}``.

    This function modifies *schema* in place and also returns it so that it
    can be used in an expression context.

    Args:
        schema: A mutable JSON schema dict produced by Pydantic.

    Returns:
        The same dict, patched for OpenAI strict compatibility where possible.
    """
    if not isinstance(schema, dict):
        return schema

    if schema.get("type") == "object" or "properties" in schema:
        props = schema.get("properties", {})
        if props:
            # Always assign (not setdefault) — Pydantic may explicitly set
            # additionalProperties:true for freeform fields; we must override.
            schema["additionalProperties"] = False
            existing = set(schema.get("required", []))
            schema["required"] = sorted(existing | set(props.keys()))
            for prop_schema in props.values():
                _make_openai_strict(prop_schema)

    if schema.get("type") == "array":
        items = schema.get("items")
        if isinstance(items, dict):
            _make_openai_strict(items)

    for sub in schema.get("$defs", {}).values():
        _make_openai_strict(sub)

    for combiner in ("anyOf", "oneOf", "allOf"):
        for sub in schema.get(combiner, []):
            _make_openai_strict(sub)

    return schema


def _has_freeform_object(node: object) -> bool:
    """Return True if any object node in the schema tree is freeform.

    A node is freeform when it has ``additionalProperties: true`` — the
    marker Pydantic emits for bare ``dict`` fields and ``list[dict]`` items.
    OpenAI's strict mode rejects any schema containing such a node with a
    400 error, causing an unnecessary fallback roundtrip.

    Args:
        node: Any value within a JSON schema tree.

    Returns:
        True if a freeform object node is detected anywhere in the tree.
    """
    if not isinstance(node, dict):
        return False
    if node.get("additionalProperties") is True:
        return True
    for value in node.values():
        if isinstance(value, dict) and _has_freeform_object(value):
            return True
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and _has_freeform_object(item):
                    return True
    return False


def _strict_schema(model_cls: type) -> dict | None:
    """Return a strict-compatible JSON schema for *model_cls*, or None.

    Derives the Pydantic schema, applies ``_make_openai_strict``, then
    checks whether any freeform object node remains. If one does, the
    schema cannot be used in strict mode and None is returned so the
    caller falls back to json_object mode without a 400 rejection.

    Args:
        model_cls: A Pydantic BaseModel subclass.

    Returns:
        A strict-compatible JSON schema dict, or None if the model
        contains freeform dict fields.
    """
    raw = model_cls.model_json_schema()
    raw.pop("title", None)
    _make_openai_strict(raw)
    if _has_freeform_object(raw):
        _logger.debug(
            "Schema for %s excluded from strict registry: "
            "contains freeform dict/list[dict] fields. "
            "LLM calls for this stage will use json_object mode.",
            model_cls.__name__,
        )
        return None
    return raw


# ---------------------------------------------------------------------------
# SCHEMAS — the single authoritative registry
# ---------------------------------------------------------------------------
# Only schemas whose model_cls passes the strict-compatibility check are
# included. Incompatible entries evaluate to None and are dropped by the
# dict comprehension, so SCHEMAS.get(key) returns None for those stages,
# which causes LLMClient to use json_object mode directly.

_ALL_SCHEMAS: dict[str, dict | None] = {
    # Stage 1 — requirement_parsing
    "requirement_parsing": _strict_schema(ParsedRequirements),

    # Stage 2 — requirement_challenge
    "requirement_challenge": _strict_schema(ChallengeOutput),

    # Stage 3 — scenario_modeling
    "scenario_modeling": _strict_schema(ScenarioOutput),

    # Stage 4 — characteristic_inference
    "characteristic_inference": _strict_schema(CharacteristicOutput),

    # Stage 4b — tactics_recommendation
    "tactics_recommendation": _strict_schema(TacticsOutput),

    # Stage 5 — conflict_analysis
    "conflict_analysis": _strict_schema(ConflictOutput),

    # Stage 6 — architecture_generation
    "architecture_generation": _strict_schema(ArchitectureDesign),

    # Stage 6b — buy_vs_build_analysis
    "buy_vs_build_analysis": _strict_schema(BuyVsBuildOutput),

    # Stage 8 — trade_off_analysis
    "trade_off_analysis": _strict_schema(TradeOffOutput),

    # Stage 9 — adl_generation
    "adl_generation": _strict_schema(ADLOutput),

    # Stage 10 — weakness_analysis
    "weakness_analysis": _strict_schema(WeaknessOutput),

    # Stage 11 — fmea_analysis
    "fmea_analysis": _strict_schema(FMEAOutput),

    # Diagram stage — one call per diagram type
    "diagram_generation_single": _strict_schema(SingleDiagramOutput),
}

SCHEMAS: dict[str, dict] = {
    k: v for k, v in _ALL_SCHEMAS.items() if v is not None
}

# Log the outcome at import time so startup logs show which stages use strict mode.
_strict_keys = sorted(SCHEMAS.keys())
_json_object_keys = sorted(k for k, v in _ALL_SCHEMAS.items() if v is None)
_logger.info(
    "Schema registry: %d strict-mode schemas (%s); "
    "%d json_object-mode schemas (%s)",
    len(_strict_keys), _strict_keys,
    len(_json_object_keys), _json_object_keys,
)

# At least the single-diagram schema must pass strict-mode checks.
# If this assertion fails, SingleDiagramOutput gained a freeform dict field.
assert "diagram_generation_single" in SCHEMAS, (
    "diagram_generation_single schema failed strict-mode compatibility check. "
    "SingleDiagramOutput must not contain bare dict or list[dict] fields."
)
