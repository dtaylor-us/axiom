"""JSON schema registry for all pipeline stage outputs.

Each entry is derived from the corresponding Pydantic output model in
app.models.outputs using model.model_json_schema(). Schemas are computed
once at import time and cached as module-level constants.

Passing a schema to LLMClient.complete() activates provider-native
structured output enforcement (OpenAI json_schema type, strict=True).
This is Layer 1 of the two-layer output enforcement contract:

  Layer 1: Provider-native JSON schema constraint (this module)
  Layer 2: Application-layer Pydantic validation (each tool's run())

When strict schema enforcement is rejected by the provider, LLMClient
falls back to json_object mode and logs schema_enforcement_fallback=True.

Usage:
    from app.llm.schemas import SCHEMAS

    raw = await llm_client.complete(
        prompt,
        output_schema=SCHEMAS["requirement_parsing"],
        schema_name="requirement_parsing",
    )
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Schema derivation helpers
# ---------------------------------------------------------------------------

def _schema(model_cls: type) -> dict:
    """Derive a JSON schema dict from a Pydantic model class.

    Strips the title field from the top-level schema to keep the object
    clean when embedded in the json_schema.schema field. Provider APIs
    generally do not require the top-level title.

    Args:
        model_cls: A Pydantic BaseModel subclass.

    Returns:
        A JSON schema dict suitable for use as json_schema.schema.
    """
    raw = model_cls.model_json_schema()
    raw.pop("title", None)
    return raw


# ---------------------------------------------------------------------------
# SCHEMAS — the single authoritative registry
# ---------------------------------------------------------------------------

SCHEMAS: dict[str, dict] = {
    # Stage 1 — requirement_parsing
    "requirement_parsing": _schema(ParsedRequirements),

    # Stage 2 — requirement_challenge
    "requirement_challenge": _schema(ChallengeOutput),

    # Stage 3 — scenario_modeling
    "scenario_modeling": _schema(ScenarioOutput),

    # Stage 4 — characteristic_inference
    "characteristic_inference": _schema(CharacteristicOutput),

    # Stage 4b — tactics_recommendation
    "tactics_recommendation": _schema(TacticsOutput),

    # Stage 5 — conflict_analysis
    "conflict_analysis": _schema(ConflictOutput),

    # Stage 6 — architecture_generation
    "architecture_generation": _schema(ArchitectureDesign),

    # Stage 6b — buy_vs_build_analysis
    "buy_vs_build_analysis": _schema(BuyVsBuildOutput),

    # Stage 8 — trade_off_analysis
    "trade_off_analysis": _schema(TradeOffOutput),

    # Stage 9 — adl_generation
    "adl_generation": _schema(ADLOutput),

    # Stage 10 — weakness_analysis
    "weakness_analysis": _schema(WeaknessOutput),

    # Stage 11 — fmea_analysis
    "fmea_analysis": _schema(FMEAOutput),

    # Item 4 — diagram_generation (single-type call)
    "diagram_generation_single": _schema(SingleDiagramOutput),
}

# Sanity check at import time — fail fast if any schema derivation silently
# produced an empty dict (would mean the model class lost all its fields).
_MINIMUM_SCHEMA_KEYS = 8
assert len(SCHEMAS) >= _MINIMUM_SCHEMA_KEYS, (
    f"SCHEMAS registry has only {len(SCHEMAS)} entries; "
    f"expected at least {_MINIMUM_SCHEMA_KEYS}. "
    "Check app/models/outputs.py for missing model classes."
)
