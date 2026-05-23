"""Unit tests for app.workshop.taxonomy."""

import pytest
from app.workshop.taxonomy import (
    CANONICAL_ATTRIBUTES,
    ALIASES,
    NON_QA_CONCEPTS,
    normalise_attribute_name,
    is_non_qa_concern,
)


def test_canonical_passthrough():
    """A name that is already canonical comes back as (canonical, canonical)."""
    cat, display = normalise_attribute_name("performance")
    assert cat == "performance"
    assert display == "performance"


def test_alias_resolution():
    """Known aliases map to their canonical form."""
    cat, display = normalise_attribute_name("resilience")
    assert cat == "availability"
    assert display == "availability"


def test_unknown_returns_other_with_raw_name():
    """An unrecognised attribute name returns ('other', raw_name)."""
    cat, display = normalise_attribute_name("quantum_cheese_resilience")
    assert cat == "other"
    assert display == "quantum_cheese_resilience"


def test_non_qa_concept_membership():
    """NON_QA_CONCEPTS contains expected non-QA terms."""
    assert len(NON_QA_CONCEPTS) > 0
    # All entries should be lowercase strings
    for concept in NON_QA_CONCEPTS:
        assert concept == concept.lower()


def test_is_non_qa_concern_positive():
    """A term in NON_QA_CONCEPTS is correctly identified."""
    assert is_non_qa_concern("gdpr") is True
    assert is_non_qa_concern("time to market") is True


def test_is_non_qa_concern_negative():
    """A quality attribute is not a non-QA concern."""
    assert is_non_qa_concern("performance") is False
    assert is_non_qa_concern("availability") is False


def test_normalise_is_case_insensitive():
    """normalise_attribute_name should handle mixed case."""
    cat, _ = normalise_attribute_name("Performance")
    assert cat == "performance"


def test_aliases_all_point_to_canonical():
    """Every alias value is a member of CANONICAL_ATTRIBUTES."""
    for alias, canonical in ALIASES.items():
        assert canonical in CANONICAL_ATTRIBUTES, (
            f"Alias '{alias}' → '{canonical}' is not in CANONICAL_ATTRIBUTES"
        )
