"""
Input analyser for the Quality Attribute Workshop.

Responsible for extracting structured facts from unstructured user
input such as meeting notes, email threads, and partial requirements.
This module is deliberately separate from the elicitor so the two
concerns — understanding what was said versus deriving what is needed
— remain decoupled.

Called by analyze_input_node. Not part of the pipeline domain.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFact:
    """
    A single fact extracted from user input.

    Facts are not quality attributes — they are evidence that may
    eventually support an attribute if enough context is gathered.
    """
    category: str  # business | usage | technical | risk
    fact: str
    source_quote: str
    confidence: str  # explicit | implied


@dataclass
class InputAnalysis:
    """
    The result of analysing one user input document.

    Carries extracted facts, implicit concerns, and an overall
    quality rating describing how information-rich the input was.
    """
    system_name: str = ""
    extracted_facts: list[ExtractedFact] = field(default_factory=list)
    implicit_concerns: list[str] = field(default_factory=list)
    input_quality: str = "sparse"
    input_quality_reason: str = ""


def parse_analysis_response(raw_json: str) -> InputAnalysis:
    """
    Parse the LLM's analyze_input JSON response into an InputAnalysis.

    Tolerates partial or malformed JSON by returning an empty analysis
    rather than raising, so a bad LLM response never aborts the session.

    Args:
        raw_json: JSON string from the LLM's analyze_input call.

    Returns:
        InputAnalysis populated from the JSON, or an empty analysis
        if the JSON is malformed.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning(
            "analyze_input response is not valid JSON — returning empty analysis"
        )
        return InputAnalysis()

    facts: list[ExtractedFact] = []
    for raw_fact in data.get("extracted_facts", []):
        try:
            facts.append(ExtractedFact(
                category=raw_fact.get("category", "business"),
                fact=raw_fact.get("fact", ""),
                source_quote=raw_fact.get("source_quote", ""),
                confidence=raw_fact.get("confidence", "implied"),
            ))
        except Exception:
            logger.warning("Malformed fact in analysis response — skipping")

    return InputAnalysis(
        system_name=data.get("system_name", ""),
        extracted_facts=facts,
        implicit_concerns=data.get("implicit_concerns", []),
        input_quality=data.get("input_quality", "sparse"),
        input_quality_reason=data.get("input_quality_reason", ""),
    )
