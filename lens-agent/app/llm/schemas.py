"""Output schemas for Lens pipeline stages.

Schemas are referenced by pipeline nodes when calling the LLM with
structured output. Keeping schemas here prevents inline schema definitions
in tool classes (ADL-091 equivalent for Lens).
"""
from __future__ import annotations

SCHEMAS: dict[str, dict] = {
    "gap_questions": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "question": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["category", "question", "rationale"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
    "gap_assessment": {
        "type": "object",
        "properties": {
            "resolved": {"type": "boolean"},
            "remaining_count": {"type": "integer"},
            "unresolvable_gaps": {
                "type": "array",
                "items": {"type": "string"},
            },
            "summary": {"type": "string"},
        },
        "required": ["resolved", "remaining_count", "unresolvable_gaps", "summary"],
        "additionalProperties": False,
    },
}
