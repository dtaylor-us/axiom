"""Deterministic Phase 3 fact extraction.

Understands the structured payload shapes produced by each Axiom pillar:

  ARCHON:     architecture_design (components, style), adl_rules, adl_blocks,
              fmea_risks, trade_offs, characteristics, tactics, weaknesses,
              buy_vs_build_analysis, governance_score
  SPECWEAVER: requirements, functional_requirements, non_functional_requirements,
              gaps, conflicts, assumptions, constraints, readiness_score
  LENS:       azureWafScorecard (pillars), atamAnalysis, seiAnalysis,
              structuralAnalysis, risks, recommendations, overallRating,
              executiveSummary

Design decisions:
- Pillar-specific extractors run first and consume all their fields.
- Generic walk only processes UNMAPPED top-level fields and never touches
  structured Archon/Lens/SpecWeaver fields again.
- Bare characteristic names without any description/level/target are
  enriched from the tactics list or skipped entirely — a name alone is not
  a useful memory entry.
- ADL governance rules are always typed DECISION regardless of keyword content.
- LLM-backed extraction in distiller.py handles prose-heavy content that the
  deterministic extractor cannot classify.
"""

from __future__ import annotations

import re
from typing import Any

from app.models.contracts import MemoryCandidate


# ---------------------------------------------------------------------------
# Type hint maps
# ---------------------------------------------------------------------------

FIELD_TYPE_HINTS: dict[str, str] = {
    # Archon
    "decisions": "DECISION",
    "architecture_decisions": "DECISION",
    "adl_rules": "DECISION",
    "adl_blocks": "DECISION",
    "adl_document": "DECISION",
    "trade_offs": "DECISION",
    "buy_vs_build_analysis": "DECISION",
    "style_selection": "DECISION",
    "architecture_style": "DECISION",
    "components": "DECISION",
    "requirements": "REQUIREMENT",
    "functional_requirements": "REQUIREMENT",
    "non_functional_requirements": "REQUIREMENT",
    "scenarios": "REQUIREMENT",
    "characteristics": "REQUIREMENT",
    "quality_attributes": "REQUIREMENT",
    "tactics": "REQUIREMENT",
    "risks": "RISK",
    "fmea_risks": "RISK",
    "weaknesses": "RISK",
    "assumptions": "ASSUMPTION",
    "constraints": "CONSTRAINT",
    "quality_scores": "QUALITY_SCORE",
    "waf_scores": "QUALITY_SCORE",
    "governance_score": "QUALITY_SCORE",
    # Lens
    "azurewafscorecard": "QUALITY_SCORE",
    "seianalysis": "QUALITY_SCORE",
    "structuralanalysis": "QUALITY_SCORE",
    "atamanalysis": "RISK",
    "recommendations": "DECISION",
    "insufficientinfofindings": "RISK",
    # SpecWeaver
    "gaps": "RISK",
    "conflicts": "RISK",
    "readiness_score": "QUALITY_SCORE",
}

TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "DECISION": (
        "decision", "decided", "choose", "chosen", "selected",
        "adopt", "adopted",
    ),
    "REQUIREMENT": (
        "requirement", "must", "shall", "needs to",
    ),
    "RISK": (
        "risk", "failure", "threat", "vulnerability", "gap",
        "weakness", "concern",
    ),
    "QUALITY_SCORE": (
        "score", "rating", "waf", "sei", "atam", "quality", "governance",
    ),
    "ASSUMPTION": ("assumption", "assume", "assuming"),
    "CONSTRAINT": ("constraint", "cannot", "limited", "bound", "compliance"),
}

# Minimum length for a generic prose fragment to be extracted.
# Short fragments extracted from unstructured text are almost always noise.
_MIN_TEXT_STATEMENT_LEN = 40

# Keys fully handled by pillar-specific extractors.
# The generic walk skips these entirely — they must NOT be re-processed.
_HANDLED_KEYS: frozenset[str] = frozenset({
    # Archon top-level
    "architecture_design", "adl_rules", "adl_blocks", "adl_document",
    "adl_source", "trade_offs", "fmea_risks", "fmea_critical_risks",
    "weaknesses", "weakness_summary", "characteristics", "scenarios",
    "buy_vs_build_analysis", "buy_vs_build_summary", "tactics",
    "tactics_summary", "governance_score", "governance_score_confidence",
    "governance_score_breakdown", "improvement_recommendations",
    "structured_output", "diagrams", "mermaid_component_diagram",
    "mermaid_sequence_diagram", "review_findings", "review_constraints",
    "characteristic_conflicts", "architecture_style_scores",
    "parsed_entities", "missing_requirements", "ambiguities",
    "hidden_assumptions", "architecture_override", "buy_vs_build_preferences",
    "clarifying_questions", "similar_past_designs", "pipeline_gaps",
    "token_usage", "conflicts",
    # Lens
    "azurewafscorecard", "atamanalysis", "seianalysis", "structuralanalysis",
    "risks", "recommendations", "executivesummary", "insufficientinfofindings",
    "overallrating", "overall_rating",
    # SpecWeaver
    "requirements", "functional_requirements", "non_functional_requirements",
    "gaps", "assumptions", "constraints", "readiness_score",
    # Metadata / noise
    "component_diagram", "sequence_diagram", "requires_tooling",
    "codegen_prompt", "tension_summary", "trade_off_dominant_tension",
})


async def extract_facts(
    session_summary: str | None = None,
    session_payload: dict | None = None,
) -> list[MemoryCandidate]:
    candidates: list[MemoryCandidate] = []
    payload = session_payload or {}

    # Pillar-specific extractors consume all structured fields first.
    archon = _extract_archon(payload)
    lens = _extract_lens(payload)
    specweaver = _extract_specweaver(payload)
    candidates.extend(archon)
    candidates.extend(lens)
    candidates.extend(specweaver)

    # Generic walk handles only unmapped top-level fields not claimed above.
    for key, value in payload.items():
        key_norm = _normalise_key(key)
        if key_norm in _HANDLED_KEYS:
            continue
        hinted_type = FIELD_TYPE_HINTS.get(key_norm) or _field_type_hint(key)
        candidates.extend(_extract_from_value(value, hinted_type, key))

    # Session summary: add a summary entry and extract labelled sentences from it.
    if session_summary and session_summary.strip():
        extracted_from_summary = _extract_from_text(session_summary)
        candidates.extend(extracted_from_summary)
        candidates.append(
            MemoryCandidate(
                memory_type="SESSION_SUMMARY",
                content=_compact(session_summary, 1200),
                rationale=(
                    "Automatic session summary captured for lineage; "
                    "not intended for context injection."
                ),
                confidence="MEDIUM",
                source_excerpt=_compact(session_summary, 500),
                tags=["session-summary"],
            )
        )

    return _dedupe(candidates)


# ---------------------------------------------------------------------------
# Archon extractor
# ---------------------------------------------------------------------------

def _extract_archon(payload: dict) -> list[MemoryCandidate]:
    """
    Extract memory candidates from Archon pipeline output.

    The payload is the normalised snake_case dict produced by
    ArchonMemoriaClient.normaliseArchonPayload(). Top-level keys:
      architecture_design, adl_rules, fmea_risks, trade_offs,
      characteristics, weaknesses, governance_score, buy_vs_build_analysis.
    """
    candidates: list[MemoryCandidate] = []

    # Archon may wrap output under 'structured_output' or present it at root.
    structured = payload.get("structured_output") or payload

    # ── Architecture design ────────────────────────────────────────────────
    arch = structured.get("architecture_design") or {}
    if isinstance(arch, dict):
        style = str(arch.get("style") or arch.get("architecture_style") or "").strip()
        if style and len(style) > 3:
            candidates.append(MemoryCandidate(
                memory_type="DECISION",
                content=f"Architecture style: {style}",
                rationale=(
                    arch.get("style_rationale") or arch.get("rationale") or
                    "Selected architecture style from Archon pipeline."
                ),
                confidence="HIGH",
                source_excerpt=style[:200],
                tags=["architecture-style", _slug(style)[:30]],
            ))
        for comp in _as_list(arch.get("components")):
            if not isinstance(comp, dict):
                continue
            name = str(comp.get("name") or comp.get("component") or "").strip()
            resp = str(comp.get("responsibility") or comp.get("description") or "").strip()
            comp_type = str(comp.get("type") or "internal").lower()
            if name and resp:
                candidates.append(MemoryCandidate(
                    memory_type="DECISION",
                    content=f"Component {name}: {resp}",
                    rationale=(
                        comp.get("rationale") or
                        "Architecture component defined in Archon session."
                    ),
                    confidence="HIGH",
                    source_excerpt=f"{name}: {resp}"[:200],
                    tags=["component", _slug(name)[:30], comp_type],
                ))

    # ── ADL rules ──────────────────────────────────────────────────────────
    # Always typed DECISION regardless of keyword content.
    # ADL rules express governance constraints — they are architectural
    # decisions about what the system MUST and MUST NOT do.
    for rule in _as_list(structured.get("adl_rules")):
        if isinstance(rule, str) and len(rule.strip()) > 20:
            candidates.append(MemoryCandidate(
                memory_type="DECISION",
                content=_compact(rule),
                rationale="ADL governance rule from Archon pipeline.",
                confidence="HIGH",
                source_excerpt=rule[:200],
                tags=["adl", "governance"],
            ))
        elif isinstance(rule, dict):
            # Archon ADL rule dicts use: subject, rule, statement, adl_source
            # Deliberately avoid 'requirement' and other misleading field names.
            subject = str(
                rule.get("subject") or
                rule.get("rule") or
                rule.get("statement") or
                rule.get("adl_source") or
                ""
            ).strip()
            rationale = str(
                rule.get("rationale") or
                rule.get("description") or
                ""
            ).strip()
            category = str(rule.get("category") or rule.get("enforcement_level") or "").lower()
            if subject and len(subject) > 10:
                candidates.append(MemoryCandidate(
                    memory_type="DECISION",
                    content=_compact(subject),
                    rationale=rationale or "ADL governance rule from Archon pipeline.",
                    confidence="HIGH",
                    source_excerpt=subject[:200],
                    tags=["adl", "governance"] + ([category] if category else []),
                ))

    # ── Trade-offs ──────────────────────────────────────────────────────────
    for tradeoff in _as_list(structured.get("trade_offs")):
        if not isinstance(tradeoff, dict):
            continue
        name = str(
            tradeoff.get("decision") or tradeoff.get("name") or tradeoff.get("title") or ""
        ).strip()
        rec = str(
            tradeoff.get("recommendation") or tradeoff.get("description") or ""
        ).strip()
        sacrifices = str(
            tradeoff.get("sacrifices_characteristics") or tradeoff.get("tradeoffs") or ""
        ).strip()
        if name and rec:
            content = f"Trade-off — {name}: {rec}"
            if sacrifices:
                content += f" (trade-off: {sacrifices})"
            candidates.append(MemoryCandidate(
                memory_type="DECISION",
                content=_compact(content),
                rationale=str(
                    tradeoff.get("rationale") or
                    "Architectural trade-off from Archon pipeline."
                ),
                confidence="HIGH",
                source_excerpt=_compact(content, 200),
                tags=["trade-off", "decision"],
            ))

    # ── FMEA risks ─────────────────────────────────────────────────────────
    for fmea in _as_list(structured.get("fmea_risks")):
        if not isinstance(fmea, dict):
            continue
        mode = str(fmea.get("failure_mode") or fmea.get("risk") or "").strip()
        effect = str(fmea.get("effect") or fmea.get("description") or "").strip()
        rpn = fmea.get("rpn") or fmea.get("risk_priority_number")
        comp = str(fmea.get("component") or fmea.get("area") or "").strip()
        mitigation = str(
            fmea.get("mitigation") or fmea.get("recommendation") or ""
        ).strip()
        if mode:
            content = f"FMEA risk — {mode}"
            if effect:
                content += f": {effect}"
            if comp:
                content += f" (component: {comp})"
            tags = ["fmea", "risk"]
            if comp:
                tags.append(_slug(comp))
            candidates.append(MemoryCandidate(
                memory_type="RISK",
                content=_compact(content),
                rationale=(
                    mitigation or
                    (f"FMEA failure mode. RPN: {rpn}." if rpn else
                     "FMEA failure mode from Archon pipeline.")
                ),
                confidence="HIGH",
                source_excerpt=_compact(content, 200),
                tags=tags,
            ))

    # ── Weaknesses ─────────────────────────────────────────────────────────
    for weakness in _as_list(structured.get("weaknesses")):
        if isinstance(weakness, str) and len(weakness.strip()) > 20:
            candidates.append(MemoryCandidate(
                memory_type="RISK",
                content=_compact(weakness),
                rationale="Architectural weakness from Archon pipeline.",
                confidence="MEDIUM",
                source_excerpt=weakness[:200],
                tags=["weakness", "risk"],
            ))
        elif isinstance(weakness, dict):
            title = str(
                weakness.get("title") or
                weakness.get("weakness") or
                weakness.get("description") or
                ""
            ).strip()
            rec = str(
                weakness.get("recommendation") or weakness.get("mitigation") or ""
            ).strip()
            severity = str(
                weakness.get("severity") or weakness.get("score") or ""
            ).strip()
            if title:
                content = f"Weakness — {title}"
                if rec:
                    content += f". Recommendation: {rec}"
                tags = ["weakness", "risk"]
                if severity:
                    tags.append(f"severity-{severity.lower()}")
                candidates.append(MemoryCandidate(
                    memory_type="RISK",
                    content=_compact(content),
                    rationale=(
                        f"Severity: {severity}." if severity else
                        "Architectural weakness from Archon pipeline."
                    ),
                    confidence="MEDIUM",
                    source_excerpt=_compact(content, 200),
                    tags=tags,
                ))

    # ── Characteristics ────────────────────────────────────────────────────
    # Build a lookup from tactic data to enrich bare characteristic names.
    # Tactics contain 'characteristic_name' + 'description' + 'concrete_application'
    # which give context for characteristics that only carry a name.
    tactic_context: dict[str, list[str]] = {}
    for tactic in _as_list(structured.get("tactics")):
        if not isinstance(tactic, dict):
            continue
        char_name = str(
            tactic.get("characteristic_name") or tactic.get("characteristic") or ""
        ).strip().lower()
        desc = str(tactic.get("description") or tactic.get("concrete_application") or "").strip()
        if char_name and desc:
            tactic_context.setdefault(char_name, []).append(desc)

    for char in _as_list(structured.get("characteristics")):
        if not isinstance(char, dict):
            continue
        name = str(
            char.get("name") or char.get("characteristic") or char.get("title") or ""
        ).strip()
        if not name:
            continue
        desc = str(
            char.get("description") or char.get("definition") or char.get("detail") or ""
        ).strip()
        level = str(
            char.get("level") or char.get("importance") or char.get("priority") or ""
        ).strip()
        target = str(
            char.get("target") or char.get("metric") or char.get("measure") or
            char.get("value") or ""
        ).strip()

        # If no description available, try to enrich from tactics
        if not desc and not target and not level:
            enrichment = tactic_context.get(name.lower(), [])
            if enrichment:
                desc = enrichment[0][:200]
            else:
                # A bare characteristic name with no context is not useful.
                # Skip it — the LLM extraction pass may find richer context.
                continue

        content_parts = [f"Quality attribute — {name}"]
        if desc:
            content_parts.append(f": {desc}")
        if target:
            content_parts.append(f" (target: {target})")
        if level:
            content_parts.append(f" (importance: {level})")

        candidates.append(MemoryCandidate(
            memory_type="REQUIREMENT",
            content=_compact("".join(content_parts)),
            rationale="Quality attribute characteristic from Archon pipeline.",
            confidence="HIGH",
            source_excerpt=_compact("".join(content_parts), 200),
            tags=["quality-attribute", _slug(name)[:30]],
        ))

    # ── Governance score ───────────────────────────────────────────────────
    gov_score = structured.get("governance_score")
    gov_confidence = str(structured.get("governance_score_confidence") or "").strip()
    if gov_score is not None:
        candidates.append(MemoryCandidate(
            memory_type="QUALITY_SCORE",
            content=(
                f"Archon governance score: {gov_score}/100" +
                (f" (confidence: {gov_confidence})" if gov_confidence else "")
            ),
            rationale="Automated governance assessment from Archon pipeline review stage.",
            confidence="HIGH",
            source_excerpt=f"governance_score={gov_score}",
            tags=["governance", "quality-score", "archon"],
        ))

    return candidates


# ---------------------------------------------------------------------------
# Lens extractor
# ---------------------------------------------------------------------------

def _extract_lens(payload: dict) -> list[MemoryCandidate]:
    """Extract from Lens review report shape (camelCase keys)."""
    candidates: list[MemoryCandidate] = []

    def _get(camel: str) -> Any:
        return payload.get(camel) or payload.get(_to_snake(camel))

    # Azure WAF pillars
    waf = _get("azureWafScorecard") or {}
    if isinstance(waf, dict):
        pillars = waf.get("pillars") or {}
        if isinstance(pillars, dict):
            for pillar_name, pillar_data in pillars.items():
                if not isinstance(pillar_data, dict):
                    continue
                score = pillar_data.get("score")
                gaps = _as_list(pillar_data.get("gaps"))
                findings = _as_list(pillar_data.get("findings"))
                if score is not None:
                    content = (
                        f"Azure WAF {pillar_name.replace('_', ' ').title()}: score {score}/5"
                    )
                    if gaps:
                        content += f". Gaps: {'; '.join(str(g) for g in gaps[:3])}"
                    candidates.append(MemoryCandidate(
                        memory_type="QUALITY_SCORE",
                        content=_compact(content),
                        rationale=(
                            f"Azure Well-Architected Framework "
                            f"{pillar_name} assessment."
                        ),
                        confidence="HIGH",
                        source_excerpt=_compact(content, 200),
                        tags=[
                            "azure-waf",
                            pillar_name.lower().replace("_", "-"),
                            "quality-score",
                        ],
                    ))
                for finding in findings:
                    if isinstance(finding, str) and len(finding) > 20:
                        candidates.append(MemoryCandidate(
                            memory_type="RISK",
                            content=_compact(finding),
                            rationale=(
                                f"Azure WAF {pillar_name} finding from Lens review."
                            ),
                            confidence="HIGH",
                            source_excerpt=finding[:200],
                            tags=[
                                "azure-waf",
                                pillar_name.lower().replace("_", "-"),
                                "finding",
                            ],
                        ))

    # Risks
    for risk in _as_list(_get("risks")):
        if not isinstance(risk, dict):
            continue
        title = str(risk.get("title") or "").strip()
        desc = str(risk.get("description") or "").strip()
        severity = str(risk.get("severity") or "").strip()
        mitigation = str(
            risk.get("mitigationStrategy") or risk.get("mitigation_strategy") or ""
        ).strip()
        framework = str(
            risk.get("frameworkReference") or risk.get("framework_reference") or ""
        ).strip()
        if title:
            content = f"Risk — {title}"
            if desc:
                content += f": {desc}"
            tags = ["risk", "lens-review"]
            if severity:
                tags.append(f"severity-{severity.lower()}")
            candidates.append(MemoryCandidate(
                memory_type="RISK",
                content=_compact(content),
                rationale=(
                    mitigation or
                    (f"Lens review risk. Framework: {framework}." if framework else
                     "Risk from Lens architecture review.")
                ),
                confidence="HIGH",
                source_excerpt=_compact(content, 200),
                tags=tags,
            ))

    # Recommendations
    for rec in _as_list(_get("recommendations")):
        if not isinstance(rec, dict):
            continue
        title = str(rec.get("title") or "").strip()
        desc = str(rec.get("description") or "").strip()
        priority = str(rec.get("priority") or "").strip()
        if title and desc:
            content = (
                f"Recommendation ({priority}) — {title}: {desc}" if priority
                else f"Recommendation — {title}: {desc}"
            )
            tags = ["recommendation", "lens-review"]
            if priority:
                tags.append(f"priority-{priority.lower()}")
            candidates.append(MemoryCandidate(
                memory_type="DECISION",
                content=_compact(content),
                rationale=f"Priority {priority} recommendation from Lens review.",
                confidence="MEDIUM",
                source_excerpt=_compact(content, 200),
                tags=tags,
            ))

    # SEI analysis
    sei = _get("seiAnalysis") or {}
    if isinstance(sei, dict):
        attributes = sei.get("attributes") or {}
        if isinstance(attributes, dict):
            for attr_name, attr_data in attributes.items():
                if not isinstance(attr_data, dict):
                    continue
                rating = str(attr_data.get("rating") or "").strip()
                tactics_missing = _as_list(attr_data.get("tactics_missing"))
                if rating:
                    missing_str = (
                        "; ".join(str(t) for t in tactics_missing[:3])
                        if tactics_missing else "none"
                    )
                    content = (
                        f"SEI {attr_name.title()}: {rating}. "
                        f"Tactics missing: {missing_str}"
                    )
                    candidates.append(MemoryCandidate(
                        memory_type="QUALITY_SCORE",
                        content=_compact(content),
                        rationale="SEI quality attribute assessment from Lens review.",
                        confidence="HIGH",
                        source_excerpt=_compact(content, 200),
                        tags=["sei", attr_name.lower(), "quality-score", "lens-review"],
                    ))

    # Overall rating
    rating = str(_get("overallRating") or _get("overall_rating") or "").strip()
    summary = str(_get("executiveSummary") or _get("executive_summary") or "").strip()
    if rating:
        candidates.append(MemoryCandidate(
            memory_type="QUALITY_SCORE",
            content=f"Lens architecture review overall rating: {rating}",
            rationale=(
                _compact(summary, 400) if summary else
                "Overall rating from Lens architecture review."
            ),
            confidence="HIGH",
            source_excerpt=f"overallRating={rating}",
            tags=[
                "lens-review", "overall-rating", "quality-score",
                rating.lower().replace("_", "-"),
            ],
        ))

    return candidates


# ---------------------------------------------------------------------------
# SpecWeaver extractor
# ---------------------------------------------------------------------------

def _extract_specweaver(payload: dict) -> list[MemoryCandidate]:
    """Extract from SpecWeaver requirements package shape."""
    candidates: list[MemoryCandidate] = []

    for req_field in (
        "requirements",
        "functional_requirements",
        "non_functional_requirements",
    ):
        for req in _as_list(payload.get(req_field)):
            if isinstance(req, str) and len(req.strip()) > 20:
                candidates.append(MemoryCandidate(
                    memory_type="REQUIREMENT",
                    content=_compact(req),
                    rationale=f"Requirement from SpecWeaver ({req_field}).",
                    confidence="HIGH",
                    source_excerpt=req[:200],
                    tags=["requirement", req_field.replace("_", "-")],
                ))
            elif isinstance(req, dict):
                statement = str(
                    req.get("statement") or req.get("content") or
                    req.get("description") or req.get("requirement") or ""
                ).strip()
                category = str(req.get("category") or req.get("type") or "").strip()
                confidence = str(req.get("confidence") or "HIGH").upper()
                source = str(req.get("source") or "").strip()
                if statement and len(statement) > 10:
                    content = f"[{category}] {statement}" if category else statement
                    candidates.append(MemoryCandidate(
                        memory_type="REQUIREMENT",
                        content=_compact(content),
                        rationale=(
                            f"Source: {source}" if source else
                            "Requirement from SpecWeaver distillation."
                        ),
                        confidence=(
                            confidence
                            if confidence in {"HIGH", "MEDIUM", "LOW", "INFERRED"}
                            else "MEDIUM"
                        ),
                        source_excerpt=statement[:200],
                        tags=["requirement"] + (
                            [_slug(category)] if category else []
                        ),
                    ))

    for gap in _as_list(payload.get("gaps")):
        if not isinstance(gap, dict):
            continue
        area = str(gap.get("area") or gap.get("category") or "").strip()
        desc = str(
            gap.get("description") or gap.get("content") or gap.get("gap") or ""
        ).strip()
        why = str(gap.get("why_it_matters") or gap.get("rationale") or "").strip()
        if desc and len(desc) > 10:
            content = (
                f"Requirements gap — {area}: {desc}" if area else
                f"Requirements gap: {desc}"
            )
            candidates.append(MemoryCandidate(
                memory_type="RISK",
                content=_compact(content),
                rationale=why or "Missing requirement identified by SpecWeaver.",
                confidence="MEDIUM",
                source_excerpt=_compact(content, 200),
                tags=["gap", "requirement-gap"] + ([_slug(area)] if area else []),
            ))

    for conflict in _as_list(payload.get("conflicts")):
        if not isinstance(conflict, dict):
            continue
        desc = str(
            conflict.get("description") or conflict.get("conflict") or ""
        ).strip()
        req_a = str(conflict.get("requirement_a") or conflict.get("side_a") or "").strip()
        req_b = str(conflict.get("requirement_b") or conflict.get("side_b") or "").strip()
        if desc or (req_a and req_b):
            content = desc or f"Conflict between: {req_a} | {req_b}"
            candidates.append(MemoryCandidate(
                memory_type="RISK",
                content=_compact(content),
                rationale=str(
                    conflict.get("resolution") or
                    "Requirements conflict identified by SpecWeaver."
                ),
                confidence="MEDIUM",
                source_excerpt=_compact(content, 200),
                tags=["conflict", "requirement-conflict"],
            ))

    for assumption in _as_list(payload.get("assumptions")):
        content = _dict_or_str(assumption, ("content", "statement", "assumption", "description"))
        if content and len(content) > 10:
            candidates.append(MemoryCandidate(
                memory_type="ASSUMPTION",
                content=_compact(content),
                rationale="Assumption identified by SpecWeaver.",
                confidence="MEDIUM",
                source_excerpt=content[:200],
                tags=["assumption"],
            ))

    for constraint in _as_list(payload.get("constraints")):
        content = _dict_or_str(constraint, ("content", "statement", "constraint", "description"))
        if content and len(content) > 10:
            candidates.append(MemoryCandidate(
                memory_type="CONSTRAINT",
                content=_compact(content),
                rationale="Constraint identified by SpecWeaver.",
                confidence="HIGH",
                source_excerpt=content[:200],
                tags=["constraint"],
            ))

    score = payload.get("readiness_score") or payload.get("readinessScore")
    if score is not None:
        candidates.append(MemoryCandidate(
            memory_type="QUALITY_SCORE",
            content=f"SpecWeaver requirements readiness score: {score}/100",
            rationale="Automated readiness assessment from SpecWeaver distillation.",
            confidence="HIGH",
            source_excerpt=f"readiness_score={score}",
            tags=["readiness", "quality-score", "specweaver"],
        ))

    return candidates


# ---------------------------------------------------------------------------
# Generic extraction helpers (for unmapped fields only)
# ---------------------------------------------------------------------------

def _extract_from_value(
    value: Any,
    hinted_type: str | None,
    source_key: str,
) -> list[MemoryCandidate]:
    """
    Generic extractor for unmapped fields. Conservative: requires longer
    content and explicit type signals to avoid storing noise.
    """
    if value is None:
        return []
    if isinstance(value, list):
        candidates: list[MemoryCandidate] = []
        for item in value:
            candidates.extend(_extract_from_value(item, hinted_type, source_key))
        return candidates
    if isinstance(value, dict):
        memory_type = hinted_type or _infer_type(
            " ".join(str(v) for v in value.values() if isinstance(v, str))
        )
        if not memory_type:
            return []  # Don't store unmapped dicts with no clear type signal
        content = _first_text(
            value,
            ("content", "decision", "statement", "title", "description", "summary"),
        )
        if not content or len(content) < 20:
            return []  # Skip short or empty content
        rationale = (
            _first_text(value, ("rationale", "reason", "context", "evidence", "impact"))
            or f"Extracted from {source_key}."
        )
        return [MemoryCandidate(
            memory_type=memory_type,
            content=_compact(content),
            rationale=_compact(rationale),
            confidence=_confidence(value),
            source_excerpt=_compact(str(value), 500),
            tags=_tags(value, memory_type, source_key),
        )]
    if isinstance(value, str):
        # Only extract from strings if a hint is provided — bare strings
        # from unknown fields are almost always noisy fragments.
        if hinted_type:
            return _extract_from_text(value, hinted_type)
    return []


def _extract_from_text(
    text: str,
    hinted_type: str | None = None,
) -> list[MemoryCandidate]:
    """
    Extract labelled sentences from prose text.

    Only extracts sentences that either:
    - Carry an explicit label prefix (Decision:, Requirement:, Risk: etc.), OR
    - Have a hinted_type AND meet a minimum length threshold.

    This prevents noise from short keyword-matching fragments.
    """
    candidates: list[MemoryCandidate] = []
    for statement in _statements(text):
        label = _label_type(statement)
        if label:
            # Explicit label always wins
            memory_type = label
        elif hinted_type and len(statement) >= _MIN_TEXT_STATEMENT_LEN:
            memory_type = hinted_type
        else:
            # Keyword match without a hint or label: require longer content
            if len(statement) < _MIN_TEXT_STATEMENT_LEN:
                continue
            memory_type = _infer_type(statement)
            if not memory_type:
                continue

        candidates.append(MemoryCandidate(
            memory_type=memory_type,
            content=_strip_label(statement),
            rationale="Extracted from labelled or keyword-bearing session text.",
            confidence="MEDIUM",
            source_excerpt=_compact(statement, 500),
            tags=_keyword_tags(statement, memory_type),
        ))
    return candidates


def _infer_type(text: str) -> str | None:
    label = _label_type(text)
    if label:
        return label
    normalized = text.lower()
    for memory_type, keywords in TYPE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return memory_type
    return None


def _label_type(text: str) -> str | None:
    m = re.match(
        r"^\s*(decision|requirement|risk|assumption|constraint|quality score)\s*[:\-]",
        text.lower(),
    )
    return m.group(1).upper().replace(" ", "_") if m else None


def _statements(text: str) -> list[str]:
    rough = re.split(r"[\n\r]+|(?<=[.!?])\s+(?=[A-Z])", text)
    return [_compact(part) for part in rough if len(part.strip()) >= 20]


def _strip_label(value: str) -> str:
    return re.sub(
        r"^\s*(decision|requirement|risk|assumption|constraint|quality score)\s*[:\-]\s*",
        "",
        value.strip(),
        flags=re.I,
    )


def _first_text(value: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _dict_or_str(value: Any, dict_keys: tuple[str, ...]) -> str | None:
    if isinstance(value, str) and len(value.strip()) > 10:
        return value.strip()
    if isinstance(value, dict):
        return _first_text(value, dict_keys)
    return None


def _confidence(value: dict) -> str:
    raw = str(value.get("confidence", "")).upper()
    return raw if raw in {"HIGH", "MEDIUM", "LOW", "INFERRED"} else "MEDIUM"


def _tags(value: dict, memory_type: str | None, source_key: str) -> list[str]:
    raw_tags = value.get("tags")
    if isinstance(raw_tags, list):
        return [str(t).strip().lower() for t in raw_tags if str(t).strip()][:8]
    return _keyword_tags(f"{source_key} {value}", memory_type)


def _keyword_tags(text: str, memory_type: str | None) -> list[str]:
    norm_type = (memory_type or _infer_type(text) or "session-summary")
    tags: set[str] = {norm_type.lower().replace("_", "-")}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}", text.lower()):
        if token not in {
            "this", "that", "with", "from", "have", "will", "must", "should",
            "architecture", "system", "service", "component", "based", "when",
            "that", "which", "they", "their", "there", "here", "such",
        }:
            tags.add(token)
        if len(tags) >= 8:
            break
    return sorted(tags)


def _compact(value: str, limit: int = 1000) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return (
        normalized if len(normalized) <= limit
        else normalized[:limit - 3].rstrip() + "..."
    )


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _slug(value: str) -> str:
    """Convert a display name to a lowercase kebab-case tag."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _normalise_key(key: str) -> str:
    """Normalise camelCase / kebab-case / space-separated key to snake_case."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
    return re.sub(r"[^a-z0-9_]", "_", snake)


def _field_type_hint(key: str) -> str | None:
    """Broad matching by stripping all non-alphanumeric characters."""
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return FIELD_TYPE_HINTS.get(normalized)


def _to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _dedupe(candidates: list[MemoryCandidate]) -> list[MemoryCandidate]:
    """
    Deduplicate by (memory_type, content[:200]).

    Because pillar-specific extractors always run before the generic walk,
    the first occurrence for any content key is always the typed, high-quality
    one. The generic walk's lower-quality duplicates are discarded.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[MemoryCandidate] = []
    for candidate in candidates:
        key = (candidate.memory_type, candidate.content.lower()[:200])
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique
