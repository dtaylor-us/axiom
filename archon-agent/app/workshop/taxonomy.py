"""
Quality attribute taxonomy for the Quality Attribute Workshop.

Defines the canonical set of quality attributes recognised by Archon,
alias mappings from common informal names, and non-QA concerns that
must be separated from the attribute list.

The taxonomy drives ConsolidationEngine to merge semantically
equivalent attributes before they reach the UI or the pipeline.

Not part of the pipeline domain. Does not import from app.pipeline.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical attribute names — one entry per distinct quality concern.
# These match the ``category`` Literal values in ElicitedAttribute.
# ---------------------------------------------------------------------------
CANONICAL_ATTRIBUTES: frozenset[str] = frozenset({
    "availability",
    "performance",
    "security",
    "modifiability",
    "scalability",
    "testability",
    "deployability",
    "usability",
    "interoperability",
    "data_integrity",
    "auditability",
    "recoverability",
    "cost",
    "other",
})

# ---------------------------------------------------------------------------
# Alias → canonical mapping.
# Keys: informal names the LLM commonly returns.
# Values: the canonical category string.
# ---------------------------------------------------------------------------
ALIASES: dict[str, str] = {
    # availability variants
    "reliability":          "availability",
    "uptime":               "availability",
    "fault tolerance":      "availability",
    "fault-tolerance":      "availability",
    "high availability":    "availability",
    "ha":                   "availability",
    "resilience":           "availability",
    "resiliency":           "availability",

    # performance variants
    "latency":              "performance",
    "throughput":           "performance",
    "response time":        "performance",
    "responsiveness":       "performance",
    "speed":                "performance",
    "efficiency":           "performance",

    # scalability variants
    "elasticity":           "scalability",
    "capacity":             "scalability",
    "load handling":        "scalability",
    "horizontal scaling":   "scalability",
    "vertical scaling":     "scalability",

    # recoverability variants
    "disaster recovery":    "recoverability",
    "recovery":             "recoverability",
    "rto":                  "recoverability",
    "rpo":                  "recoverability",
    "backup":               "recoverability",
    "restore":              "recoverability",

    # security variants
    "authentication":       "security",
    "authorisation":        "security",
    "authorization":        "security",
    "access control":       "security",
    "confidentiality":      "security",
    "integrity":            "data_integrity",
    "data protection":      "security",
    "encryption":           "security",

    # auditability variants
    "audit":                "auditability",
    "logging":              "auditability",
    "traceability":         "auditability",
    "observability":        "auditability",
    "monitoring":           "auditability",
    "compliance":           "auditability",
    "regulatory compliance": "auditability",

    # modifiability variants
    "maintainability":      "modifiability",
    "extensibility":        "modifiability",
    "flexibility":          "modifiability",
    "changeability":        "modifiability",
    "evolvability":         "modifiability",

    # deployability variants
    "operability":          "deployability",
    "cicd":                 "deployability",
    "ci/cd":                "deployability",
    "continuous deployment": "deployability",
    "zero downtime":        "deployability",

    # testability variants
    "verifiability":        "testability",
    "debuggability":        "testability",

    # interoperability variants
    "portability":          "interoperability",
    "compatibility":        "interoperability",
    "integration":          "interoperability",
    "api compatibility":    "interoperability",

    # data_integrity variants
    "consistency":          "data_integrity",
    "data quality":         "data_integrity",
    "accuracy":             "data_integrity",
    "correctness":          "data_integrity",

    # usability variants
    "ux":                   "usability",
    "user experience":      "usability",
    "accessibility":        "usability",
    "learnability":         "usability",

    # cost variants
    "cost efficiency":      "cost",
    "cost optimisation":    "cost",
    "cost optimization":    "cost",
    "budget":               "cost",
    "cloud cost":           "cost",
}

# ---------------------------------------------------------------------------
# Non-QA concerns — topics the LLM sometimes surfaces as attributes but
# that are NOT measurable quality attributes.  These are separated from
# the attribute list and placed in WorkshopContext.non_qa_concerns instead.
# ---------------------------------------------------------------------------
NON_QA_CONCEPTS: frozenset[str] = frozenset({
    # Team / process concerns
    "team size",
    "staffing",
    "hiring",
    "training",
    "documentation",
    "process",
    "agile",
    "sprint",
    "velocity",
    "technical debt",

    # Business / commercial concerns
    "time to market",
    "time-to-market",
    "feature completeness",
    "market fit",
    "product roadmap",
    "vendor lock-in",
    "vendor lock in",
    "licensing",

    # Legal / governance
    "gdpr",
    "hipaa",
    "iso 27001",
    "soc 2",
    "legal",
    "regulatory",
    "governance",
    "privacy policy",

    # Infrastructure topology (not a QA per se)
    "multi-region",
    "multi region",
    "geo-redundancy",
    "on-premise",
    "on-prem",
    "cloud migration",
    "lift and shift",
})


def normalise_attribute_name(raw_name: str) -> tuple[str, str]:
    """
    Map a raw attribute name to its canonical category and normalised name.

    Returns a 2-tuple of (canonical_category, normalised_display_name).

    The canonical category is used to group and deduplicate attributes.
    If the raw name matches an alias, the alias's canonical is returned.
    If the name is unrecognised, ``("other", raw_name)`` is returned so
    the attribute is not silently dropped.

    Args:
        raw_name: Attribute name as produced by the LLM, e.g. "resilience".

    Returns:
        Tuple of (canonical_category, normalised_display_name).

    Examples:
        >>> normalise_attribute_name("resilience")
        ("availability", "availability")
        >>> normalise_attribute_name("availability")
        ("availability", "availability")
        >>> normalise_attribute_name("team size")
        ("other", "team size")   # caller checks NON_QA_CONCEPTS separately
    """
    lower = raw_name.strip().lower()

    # Direct match against canonical set
    if lower in CANONICAL_ATTRIBUTES:
        return lower, lower

    # Alias lookup
    if lower in ALIASES:
        canonical = ALIASES[lower]
        return canonical, canonical

    # No match — preserve raw name under "other"
    return "other", raw_name.strip()


def is_non_qa_concern(raw_name: str) -> bool:
    """
    Return True when the name describes a non-QA concern.

    Args:
        raw_name: Name string to check.

    Returns:
        True if the name appears in NON_QA_CONCEPTS (case-insensitive).
    """
    return raw_name.strip().lower() in NON_QA_CONCEPTS
