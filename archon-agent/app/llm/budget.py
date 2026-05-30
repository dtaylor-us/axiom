"""
Context budget utilities for local Ollama inference.

Ollama enforces ``num_ctx`` as a hard limit. These helpers trim large,
variable prompt inputs before template rendering so important fixed
instructions and reserved output space remain intact.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 3
OPENAI_INPUT_BUDGET_TOKENS = 64000
OLLAMA_INPUT_FRACTION = 0.50
OLLAMA_LARGE_OUTPUT_INPUT_FRACTION = 0.35

LARGE_OUTPUT_STAGES = {
    "architecture_generation",
    "fmea_analysis",
    "adl_generation",
}


def budget_json_list(
    items: list[dict],
    max_tokens: int,
    stage_name: str = "",
    item_label: str = "items",
) -> list[dict]:
    """
    Truncate a JSON-serialisable list to a token budget.

    Args:
        items: JSON-serialisable dictionaries to include.
        max_tokens: Maximum tokens available for the list.
        stage_name: Stage name used in warning logs.
        item_label: Human-readable item label for warning logs.

    Returns:
        Prefix of ``items`` that fits within the budget.
    """
    if not items:
        return items

    max_chars = max_tokens * CHARS_PER_TOKEN
    result: list[dict] = []
    total_chars = 0

    for item in items:
        item_json = json.dumps(item, default=str)
        item_size = len(item_json)
        if total_chars + item_size > max_chars:
            logger.warning(
                "BUDGET: truncated %s list. stage=%s kept=%d of=%d "
                "budget_tokens=%d",
                item_label,
                stage_name,
                len(result),
                len(items),
                max_tokens,
            )
            break
        result.append(item)
        total_chars += item_size

    return result


def budget_string(
    text: str,
    max_tokens: int,
    stage_name: str = "",
    field_name: str = "text",
) -> str:
    """
    Truncate a string to fit within a token budget.

    Args:
        text: Text to potentially truncate.
        max_tokens: Maximum tokens available for this field.
        stage_name: Stage name used in warning logs.
        field_name: Field name used in warning logs.

    Returns:
        Original text when it fits, otherwise a truncated string with notice.
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text

    logger.warning(
        "BUDGET: truncated string field. stage=%s field=%s "
        "original_chars=%d budget_chars=%d",
        stage_name,
        field_name,
        len(text),
        max_chars,
    )
    return text[:max_chars] + "\n[... truncated to fit context budget ...]"


def get_input_budget(
    stage_name: str,
    provider: str = "ollama",
    num_ctx: int = 16384,
) -> int:
    """
    Return the prompt input-context budget for a stage.

    Args:
        stage_name: Pipeline or workshop stage name.
        provider: Active provider name.
        num_ctx: Context window for the selected local model.

    Returns:
        Token budget for variable prompt inputs.
    """
    if provider == "openai":
        return OPENAI_INPUT_BUDGET_TOKENS

    if stage_name in LARGE_OUTPUT_STAGES:
        return int(num_ctx * OLLAMA_LARGE_OUTPUT_INPUT_FRACTION)
    return int(num_ctx * OLLAMA_INPUT_FRACTION)
