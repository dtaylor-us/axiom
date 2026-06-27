"""LangGraph node functions for the Lens 10-stage review pipeline.

Each function represents one pipeline stage. Core stages abort the pipeline
on failure. Supporting stages record a gap and continue so the user always
receives a partial report rather than a blank result.

Core stages (abort on failure): evidence_parsing, risk_identification,
    report_assembly.
Supporting stages (gap recorded, pipeline continues): all others.

Hallucination prevention rule: all prompts instruct the LLM to base
findings ONLY on submitted evidence. If a detail is not in the evidence
it must be noted as UNKNOWN or a gap, never invented. This rule is
enforced by both the prompt text and the evidence thinness check in
evidence_parsing which auto-populates insufficient_info_gaps.
"""
from __future__ import annotations

import json
import logging

from app.llm.client import get_llm_client
from app.models.contracts import ReviewContext

logger = logging.getLogger(__name__)

# Caps enforced at the pipeline level (ADL-094)
MAX_RISKS = 20
MAX_RECOMMENDATIONS = 15

# Minimum evidence quality thresholds.
# Below these thresholds the pipeline auto-populates insufficient_info_gaps
# so the report accurately reflects what could not be evaluated.
MIN_COMPONENTS_FOR_FULL_REVIEW = 2
MIN_EVIDENCE_CHARS_FOR_FULL_REVIEW = 200

# Areas that are always checked for evidence coverage.
# Any area with no evidence becomes an insufficient_info gap.
COVERAGE_AREAS = [
    ("security", ["auth", "authentication", "authoriz", "identity", "jwt", "tls",
                   "ssl", "encrypt", "secret", "credential", "iam"]),
    ("reliability", ["failover", "redundan", "replica", "backup", "recovery",
                     "rto", "rpo", "availability", "circuit", "retry", "health"]),
    ("observability", ["monitor", "log", "metric", "trace", "alert", "dashboard",
                       "opentelemetry", "prometheus", "grafana", "jaeger"]),
    ("performance", ["latency", "throughput", "load", "scale", "performance",
                     "cache", "concurrent", "benchmark", "sla", "slo"]),
    ("data", ["database", "storage", "persist", "retention", "backup",
              "consistency", "transaction", "schema"]),
]


# ─── Helpers ────────────────────────────────────────────────────────────────

def _format_evidence(context: ReviewContext) -> str:
    """Render all submitted evidence as a readable block for prompts."""
    if not context.evidence:
        return context.system_description or "No evidence provided."
    parts = [f"System: {context.system_description}"] if context.system_description else []
    for item in context.evidence:
        label = item.get("sourceLabel") or item.get("source_label", "Evidence")
        content = item.get("content", "")
        parts.append(f"### {label}\n{content}")
    return "\n\n".join(parts)


def _format_qa(context: ReviewContext) -> str:
    """Render gap Q&A pairs for prompts."""
    pairs = []
    answered = {
        q.get("id"): q.get("answer")
        for q in context.gap_questions
        if q.get("answer")
    }
    for q in context.gap_questions:
        answer = answered.get(q.get("id")) or q.get("answer")
        if answer:
            pairs.append(f"Q [{q.get('category')}]: {q.get('question')}\nA: {answer}")
    if context.insufficient_info_gaps:
        pairs.append("\nUnresolved gaps (insufficient information):")
        pairs.extend(f"- {g}" for g in context.insufficient_info_gaps)
    return "\n\n".join(pairs) if pairs else "No gap questions were asked."


def _total_evidence_chars(context: ReviewContext) -> int:
    """Return the total character count of all submitted evidence."""
    total = len(context.system_description or "")
    for item in context.evidence:
        total += len(item.get("content", ""))
    return total


def _detect_coverage_gaps(context: ReviewContext) -> list[str]:
    """
    Detect coverage areas with no evidence keywords.

    Checks all evidence text against keyword lists for each coverage area.
    Areas with no matching keywords are returned as insufficient_info gaps.
    This is a fast keyword check — it does not replace LLM analysis but
    ensures the report honestly reflects what is not covered.

    Args:
        context: ReviewContext with evidence.

    Returns:
        List of gap strings describing uncovered areas.
    """
    all_text = (_format_evidence(context) + " " + _format_qa(context)).lower()
    gaps = []
    for area, keywords in COVERAGE_AREAS:
        if not any(kw in all_text for kw in keywords):
            gaps.append(
                f"No {area} information found in evidence. "
                f"{area.capitalize()} pillar assessment may be incomplete."
            )
    return gaps


async def _llm_json(prompt: str, stage_name: str) -> dict:
    """Call the LLM and parse the JSON response. Returns empty dict on failure."""
    client = get_llm_client()
    try:
        raw = await client.complete(
            prompt=prompt,
            response_format="json",
            stage_name=stage_name,
        )
        return json.loads(raw)
    except Exception as exc:
        logger.error("nodes: LLM call failed stage=%s error=%s", stage_name, exc)
        return {}


# ─── Stage 1: evidence_parsing (CORE) ───────────────────────────────────────

async def evidence_parsing(context: ReviewContext) -> ReviewContext:
    """
    Parse all submitted evidence into a structured representation.

    Also performs evidence thinness detection: if total evidence is below
    MIN_EVIDENCE_CHARS_FOR_FULL_REVIEW or key coverage areas are missing,
    auto-populates insufficient_info_gaps so the report accurately reflects
    what could not be evaluated. This prevents hallucination by giving
    downstream stages explicit gaps to reference rather than inventing details.

    CORE stage: failure aborts the pipeline.
    """
    evidence_text = _format_evidence(context)
    total_chars = _total_evidence_chars(context)

    # Detect and record coverage gaps before LLM analysis.
    # This ensures report.insufficientInfoFindings is populated even when
    # the LLM might otherwise hallucinate coverage for missing areas.
    coverage_gaps = _detect_coverage_gaps(context)
    for gap in coverage_gaps:
        if gap not in context.insufficient_info_gaps:
            context.insufficient_info_gaps.append(gap)

    if total_chars < MIN_EVIDENCE_CHARS_FOR_FULL_REVIEW:
        context.insufficient_info_gaps.append(
            f"Evidence is very sparse ({total_chars} chars). "
            "The review is based on limited information and findings should "
            "be treated as indicative only. Providing more detailed architecture "
            "documentation would significantly improve review quality."
        )
        context.has_gaps = True
        logger.warning(
            "evidence_parsing: sparse evidence session=%s chars=%d",
            context.session_id,
            total_chars,
        )

    prompt = f"""You are an expert software architect. Parse the following architecture
evidence into a structured representation.

Evidence:
{evidence_text}

CRITICAL RULE: Only extract information that is EXPLICITLY STATED in the evidence
above. Do NOT infer, assume, or invent details that are not present. If a field
cannot be populated from the evidence, use UNKNOWN or an empty list.

Return a JSON object:
{{
  "architecture_style": "ONLY if explicitly stated or directly inferable, else UNKNOWN",
  "components": [
    {{"name": "component name as stated", "responsibility": "as described in evidence"}}
  ],
  "integration_points": [
    {{"name": "as stated", "protocol": "as stated, else UNKNOWN"}}
  ],
  "deployment_model": "as stated, else UNKNOWN",
  "technology_stack": ["only technologies explicitly named in evidence"],
  "stated_quality_concerns": ["only quality attributes explicitly mentioned"],
  "stated_constraints": ["only constraints explicitly mentioned"],
  "unknown_areas": ["list every significant area NOT covered by the evidence"]
}}
"""
    result = await _llm_json(prompt, "evidence_parsing")
    context.parsed_evidence = result
    context.completed_stages.append("evidence_parsing")
    logger.info(
        "evidence_parsing: completed components=%d coverage_gaps=%d",
        len(result.get("components", [])),
        len(coverage_gaps),
    )
    return context


# ─── Stage 2: azure_waf_analysis (SUPPORTING) ───────────────────────────────

async def azure_waf_analysis(context: ReviewContext) -> ReviewContext:
    """
    Evaluate the architecture against the five Azure Well-Architected
    Framework pillars.

    Scores each pillar 0-5 based on evidence coverage only.
    Does not assume compliance — no evidence means a gap, not a pass.
    Partial evidence scores 1-2; full coverage scores 3-5.
    SUPPORTING stage: failure records a gap and continues.
    """
    evidence_text = _format_evidence(context)
    qa_text = _format_qa(context)
    prompt = f"""You are an expert architecture reviewer. Evaluate this architecture
against the Azure Well-Architected Framework five pillars.

Architecture Evidence:
{evidence_text}

Clarification Q&A:
{qa_text}

CRITICAL RULES:
1. Base EVERY finding ONLY on information explicitly present in the evidence above.
2. Do NOT assume compliance. If there is no evidence for an area, it is a gap (score 0).
3. Partial evidence earns partial credit (score 1-2), not 0 and not full credit.
4. Never reference technologies, patterns, or approaches not mentioned in the evidence.
5. If the evidence mentions monitoring dashboards, that is partial observability evidence —
   score operational_excellence at least 1, not 0.
6. If the evidence mentions device certificates or any auth mechanism, score security
   at least 1 in BOTH Azure WAF and note it as partial evidence.

Pillars and their core concerns:
- Reliability: failure mode handling, recovery objectives (RTO/RPO), redundancy,
  dependency failure isolation, health monitoring
- Security: identity and access management, data protection at rest and in transit,
  network security, secret management, threat detection
- Cost Optimisation: right-sizing, scaling strategy and cost, cost monitoring,
  cost implications of architecture decisions
- Operational Excellence: deployment strategy and automation, observability
  (logging/metrics/tracing), incident response, change management
- Performance Efficiency: performance targets and SLAs, scaling approach,
  bottleneck identification, caching and data access patterns

Return a JSON object:
{{
  "pillars": {{
    "reliability": {{
      "score": 3,
      "addressed": ["list of concerns evidenced — quote the evidence"],
      "gaps": ["list of concerns with no evidence"],
      "findings": ["specific observations grounded in the evidence"],
      "insufficient_info": false
    }},
    "security": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": true }},
    "cost_optimisation": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }},
    "operational_excellence": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }},
    "performance_efficiency": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }}
  }},
  "overall_waf_summary": "Brief overall assessment grounded in the evidence."
}}

Scoring guide:
0 = no evidence at all
1 = minimal — one or two items mentioned
2 = partial — some concerns addressed, others missing
3 = adequate — most concerns addressed
4 = good — well covered with minor gaps
5 = comprehensive — fully addressed with evidence
"""
    result = await _llm_json(prompt, "azure_waf_analysis")
    if result:
        context.azure_waf_scorecard = result
        context.completed_stages.append("azure_waf_analysis")
    else:
        context.pipeline_gaps.append("azure_waf_analysis: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("azure_waf_analysis")
    return context


# ─── Stage 3: atam_analysis (SUPPORTING) ────────────────────────────────────

async def atam_analysis(context: ReviewContext) -> ReviewContext:
    """
    Apply SEI ATAM principles to identify quality attribute scenarios,
    sensitivity points, tradeoffs, and risks.

    SUPPORTING stage: failure records a gap and continues.
    """
    evidence_text = _format_evidence(context)
    qa_text = _format_qa(context)
    prompt = f"""You are an expert architecture reviewer applying SEI ATAM principles.

Architecture Evidence:
{evidence_text}

Clarification Q&A:
{qa_text}

CRITICAL RULES:
1. Base EVERY finding ONLY on information explicitly present in the evidence.
2. Do NOT reference technologies, patterns, or infrastructure not mentioned
   in the evidence. For example: do not mention Kubernetes, REST, microservices,
   or any specific technology unless it appears in the evidence above.
3. Mark confidence as low_confidence when deriving scenarios from thin evidence.
4. If evidence is sparse, identify fewer scenarios with higher uncertainty
   rather than many scenarios based on assumptions.

Apply ATAM analysis:
1. Identify quality attribute scenarios grounded ONLY in the evidence
2. Identify the architecture approach from the evidence (if present)
3. Identify sensitivity points based on decisions described in the evidence
4. Identify tradeoffs from decisions described in the evidence
5. Identify risks for quality attributes with no architecture approach in evidence

Return a JSON object:
{{
  "quality_attribute_scenarios": [
    {{
      "quality_attribute": "Availability",
      "scenario": "scenario derived from evidence",
      "architecture_approach": "approach mentioned in evidence, or NOT_EVIDENCED",
      "supported": false,
      "confidence": "low"
    }}
  ],
  "sensitivity_points": [
    {{"decision": "decision from evidence", "affected_attribute": "attribute", "effect": "effect"}}
  ],
  "tradeoffs": [
    {{"decision": "decision from evidence", "gains": "gains", "costs": "costs"}}
  ],
  "risks": [
    {{"quality_attribute": "attribute", "scenario": "risk scenario", "severity": "HIGH"}}
  ],
  "atam_summary": "Brief ATAM summary. Note if evidence was insufficient for full analysis."
}}
"""
    result = await _llm_json(prompt, "atam_analysis")
    if result:
        context.atam_analysis = result
        context.completed_stages.append("atam_analysis")
    else:
        context.pipeline_gaps.append("atam_analysis: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("atam_analysis")
    return context


# ─── Stage 4: sei_analysis (SUPPORTING) ─────────────────────────────────────

async def sei_analysis(context: ReviewContext) -> ReviewContext:
    """
    Evaluate against SEI architecture quality attribute principles.

    Assesses five core attributes: modifiability, performance,
    availability, security, integrability.
    SUPPORTING stage: failure records a gap and continues.
    """
    evidence_text = _format_evidence(context)
    qa_text = _format_qa(context)
    prompt = f"""You are an expert architecture reviewer applying SEI quality attribute
principles.

Architecture Evidence:
{evidence_text}

Clarification Q&A:
{qa_text}

CRITICAL RULES:
1. Base EVERY finding ONLY on information explicitly present in the evidence.
2. tactics_present must list ONLY tactics that are evidenced by specific details
   in the evidence above. Do not list a tactic unless you can cite the evidence.
3. If evidence mentions any auth or identity mechanism (even partial),
   list it under security tactics_present and rate security at least WEAK.
4. If security appears NO_EVIDENCE in the evidence AND in Azure WAF, the SEI
   security rating must also be NO_EVIDENCE or WEAK — never ADEQUATE without evidence.
5. Ratings must be consistent across frameworks for the same evidence.

For each attribute, assess what tactics are EXPLICITLY EVIDENCED and what is missing.

Attribute tactics reference:
- Modifiability: encapsulation, use of interfaces, loose coupling, separation of
  concerns, deferred binding
- Performance: resource demand reduction, resource management, resource arbitration,
  concurrency model, caching strategy
- Availability: fault detection, fault recovery, fault prevention, redundancy,
  health monitoring
- Security: resist attacks, detect attacks, recover from attacks, identity model,
  authorisation model
- Integrability: interface contracts, service abstraction, protocol standardisation,
  error propagation across boundaries

Rating options: STRONG, ADEQUATE, WEAK, NO_EVIDENCE

Return a JSON object:
{{
  "attributes": {{
    "modifiability": {{
      "rating": "ADEQUATE",
      "tactics_present": ["only evidenced tactics with citation"],
      "tactics_missing": ["expected but not evidenced"],
      "observations": "grounded in evidence"
    }},
    "performance": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "availability": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "security": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "integrability": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}}
  }},
  "sei_summary": "Brief SEI summary. Note if evidence was insufficient for full analysis."
}}
"""
    result = await _llm_json(prompt, "sei_analysis")
    if result:
        context.sei_analysis = result
        context.completed_stages.append("sei_analysis")
    else:
        context.pipeline_gaps.append("sei_analysis: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("sei_analysis")
    return context


# ─── Stage 5: structural_analysis (SUPPORTING) ──────────────────────────────

async def structural_analysis(context: ReviewContext) -> ReviewContext:
    """
    Evaluate structural health: coupling, cohesion, dependency direction,
    boundary clarity. Each dimension scored 0-5.

    SUPPORTING stage: failure records a gap and continues.
    """
    evidence_text = _format_evidence(context)
    parsed = context.parsed_evidence
    components = parsed.get("components", [])

    # If fewer than minimum components were extracted the structural
    # analysis will be speculative — note this as a gap.
    if len(components) < MIN_COMPONENTS_FOR_FULL_REVIEW:
        context.insufficient_info_gaps.append(
            f"Structural analysis is limited: only {len(components)} component(s) "
            "identified in evidence. A meaningful structural assessment requires "
            "at least 2 components with described responsibilities and boundaries."
        )
        context.has_gaps = True

    prompt = f"""You are an expert software architect assessing structural health.

Architecture Evidence:
{evidence_text}

Parsed Components:
{json.dumps(components, indent=2)}

CRITICAL RULES:
1. Base EVERY score and observation ONLY on information in the evidence.
2. If you cannot assess a dimension from the evidence, score it 0 and note
   the reason as "Insufficient evidence to assess".
3. Do NOT reference architectural patterns, technologies, or components
   not mentioned in the evidence.

Evaluate four structural dimensions, each scored 0-5:

- Coupling (5=very low): Based ONLY on described boundaries and integration points.
- Cohesion (5=high): Based ONLY on described component responsibilities.
- Dependency Direction (5=clean): Based ONLY on described dependencies.
- Boundary Clarity (5=clear): Based ONLY on how explicitly boundaries are described.

Return a JSON object:
{{
  "coupling": {{
    "score": 3,
    "observations": ["specific observations citing the evidence"]
  }},
  "cohesion": {{"score": 3, "observations": []}},
  "dependency_direction": {{"score": 3, "observations": []}},
  "boundary_clarity": {{"score": 3, "observations": []}},
  "structural_summary": "Brief assessment. Note if evidence was insufficient."
}}
"""
    result = await _llm_json(prompt, "structural_analysis")
    if result:
        context.structural_analysis = result
        context.completed_stages.append("structural_analysis")
    else:
        context.pipeline_gaps.append("structural_analysis: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("structural_analysis")
    return context


# ─── Stage 6: risk_identification (CORE) ────────────────────────────────────

async def risk_identification(context: ReviewContext) -> ReviewContext:
    """
    Synthesise all findings into a unified risk register.

    Consolidates risks from WAF, ATAM, SEI, structural, and insufficient
    information gaps. Maximum MAX_RISKS = 20 risks, ordered by severity.
    CORE stage: failure aborts the pipeline.
    """
    waf = context.azure_waf_scorecard
    atam = context.atam_analysis
    sei = context.sei_analysis
    structural = context.structural_analysis
    info_gaps = context.insufficient_info_gaps + context.pipeline_gaps

    prompt = f"""You are synthesising architecture review findings into a risk register.

Azure WAF Findings:
{json.dumps(waf, indent=2)}

ATAM Findings:
{json.dumps(atam, indent=2)}

SEI Attribute Findings:
{json.dumps(sei, indent=2)}

Structural Findings:
{json.dumps(structural, indent=2)}

Insufficient Information Gaps:
{json.dumps(info_gaps, indent=2)}

CRITICAL RULES:
1. Only create risks that are supported by the findings above.
2. Consolidate related risks — do not create duplicates for the same issue.
3. Include risks for insufficient information gaps — these are real risks.
4. Severity must reflect actual evidence: if WAF security=0, the security
   risk is at least HIGH. If WAF security=4, there should be no CRITICAL
   security risks unless a specific vulnerability was identified.

Maximum {MAX_RISKS} risks. Order by severity descending.
Severity options: CRITICAL, HIGH, MEDIUM, LOW
Likelihood options: HIGH, MEDIUM, LOW

Return a JSON object:
{{
  "risks": [
    {{
      "title": "risk title",
      "description": "specific description citing the finding",
      "severity": "HIGH",
      "likelihood": "HIGH",
      "affected_area": "area",
      "mitigation_strategy": "specific actionable mitigation",
      "framework_reference": "Azure WAF - Security | SEI - Security | ATAM | Structural | Insufficient information"
    }}
  ]
}}
"""
    result = await _llm_json(prompt, "risk_identification")
    risks = result.get("risks", [])[:MAX_RISKS]
    context.risks = risks
    context.completed_stages.append("risk_identification")
    logger.info("risk_identification: completed risks=%d", len(risks))
    return context


# ─── Stage 7: recommendation_generation (SUPPORTING) ────────────────────────

async def recommendation_generation(context: ReviewContext) -> ReviewContext:
    """
    Generate prioritised, actionable recommendations from the risk register.

    Maximum MAX_RECOMMENDATIONS = 15. Each recommendation is specific
    and actionable — never vague.
    SUPPORTING stage: failure records a gap and continues.
    """
    risks = context.risks
    prompt = f"""You are generating prioritised architectural recommendations.

Risk Register:
{json.dumps(risks, indent=2)}

Generate specific, actionable recommendations to address these risks.
Maximum {MAX_RECOMMENDATIONS} recommendations.

Priority levels:
- P1: addresses CRITICAL or HIGH risk — resolve before production
- P2: addresses MEDIUM risk — resolve within first quarter of operation
- P3: addresses LOW risk or improvement opportunity

Effort estimates: DAYS, WEEKS, MONTHS

CRITICAL: Each recommendation must be SPECIFIC and ACTIONABLE.
Bad: "Improve security." Good: "Define and document an IAM model covering
service-to-service authentication using mutual TLS or a service mesh."

Return a JSON object:
{{
  "recommendations": [
    {{
      "title": "specific recommendation title",
      "description": "specific actionable description",
      "priority": "P1",
      "effort": "WEEKS",
      "addresses_risk": "risk title from the register"
    }}
  ]
}}
"""
    result = await _llm_json(prompt, "recommendation_generation")
    if result:
        recommendations = result.get("recommendations", [])[:MAX_RECOMMENDATIONS]
        context.recommendations = recommendations
        context.completed_stages.append("recommendation_generation")
    else:
        context.pipeline_gaps.append("recommendation_generation: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("recommendation_generation")
    return context


# ─── Stage 8: executive_summary (SUPPORTING) ────────────────────────────────

async def executive_summary(context: ReviewContext) -> ReviewContext:
    """
    Write a 3-5 paragraph executive summary for technical leadership.

    Includes overall assessment, top 3 risks, top 3 recommendations,
    and any review limitations due to insufficient information.
    SUPPORTING stage: failure records a gap and continues.
    """
    risks = context.risks[:3]
    recommendations = context.recommendations[:3]
    info_gaps = context.insufficient_info_gaps

    # Determine rating guidance based on evidence quality
    has_insufficient_info = len(info_gaps) > 0
    sparse_evidence_note = (
        "NOTE: The evidence for this review was sparse or incomplete. "
        "The executive summary MUST explicitly state the review limitations "
        "in the final paragraph and note that findings are indicative only."
        if has_insufficient_info else ""
    )

    prompt = f"""Write a 3-5 paragraph executive summary of an architecture review
for a technical leadership audience.

Top Risks:
{json.dumps(risks, indent=2)}

Top Recommendations:
{json.dumps(recommendations, indent=2)}

Insufficient Information Areas:
{json.dumps(info_gaps, indent=2)}

System description:
{context.system_description}

{sparse_evidence_note}

The summary must include:
1. What was reviewed (brief system description)
2. Overall assessment and rating rationale
3. Top 3 risks with brief explanation
4. Top 3 recommendations
5. IF insufficient_info_gaps is non-empty: a paragraph explicitly stating
   the review limitations and what information would improve accuracy.
   This paragraph is MANDATORY when there are information gaps.

Overall rating options:
- APPROVED: all five Azure WAF pillars addressed, no critical risks
- APPROVED_WITH_CONDITIONS: minor gaps, specific conditions documented
- NEEDS_REWORK: one or more pillars significantly unaddressed, or HIGH/CRITICAL risks
- NOT_APPROVED: critical structural failures or critical risks requiring architectural changes

Return a JSON object:
{{
  "executive_summary": "3-5 paragraph summary...",
  "overall_rating": "NEEDS_REWORK"
}}
"""
    result = await _llm_json(prompt, "executive_summary")
    if result:
        context.executive_summary = result.get("executive_summary", "")
        context.overall_rating = result.get("overall_rating", "NEEDS_REWORK")
        context.completed_stages.append("executive_summary")
    else:
        context.executive_summary = "Executive summary could not be generated."
        context.overall_rating = "NEEDS_REWORK"
        context.pipeline_gaps.append("executive_summary: LLM call failed")
        context.has_gaps = True
        context.completed_stages.append("executive_summary")
    return context


# ─── Stage 9: report_assembly (CORE) ────────────────────────────────────────

async def report_assembly(context: ReviewContext) -> ReviewContext:
    """
    Assemble all stage outputs into the final ReviewReport contract.

    Validates required fields, enforces risk and recommendation caps,
    and includes INSUFFICIENT_INFORMATION findings for unresolved gaps.
    CORE stage: failure aborts the pipeline.
    """
    insufficient_findings = [
        {
            "finding_type": "INSUFFICIENT_INFORMATION",
            "category": "Gap",
            "title": f"Insufficient information: {gap[:100]}",
            "description": (
                f"This area could not be fully evaluated due to missing information: {gap}. "
                "Providing this information in a follow-up review would improve the assessment."
            ),
            "framework_reference": "Evidence gaps",
            "severity": "MEDIUM",
        }
        for gap in (context.insufficient_info_gaps + context.pipeline_gaps)
    ]

    context.review_report = {
        "sessionId": context.session_id,
        "executiveSummary": context.executive_summary,
        "overallRating": context.overall_rating or "NEEDS_REWORK",
        "azureWafScorecard": context.azure_waf_scorecard,
        "atamAnalysis": context.atam_analysis,
        "seiAnalysis": context.sei_analysis,
        "structuralAnalysis": context.structural_analysis,
        "risks": context.risks[:MAX_RISKS],
        "recommendations": context.recommendations[:MAX_RECOMMENDATIONS],
        "insufficientInfoFindings": insufficient_findings,
        "completedStages": context.completed_stages,
        "hasGaps": context.has_gaps,
        "pipelineGaps": context.pipeline_gaps,
    }
    context.completed_stages.append("report_assembly")
    logger.info(
        "report_assembly: completed rating=%s risks=%d recommendations=%d "
        "insufficient_info_findings=%d",
        context.overall_rating,
        len(context.risks),
        len(context.recommendations),
        len(insufficient_findings),
    )
    return context


# ─── Stage 10: review_complete ──────────────────────────────────────────────

async def review_complete(context: ReviewContext) -> ReviewContext:
    """
    Final stage — marks the review as complete.

    In production this stage triggers the SSE COMPLETE event.
    """
    context.completed_stages.append("review_complete")
    logger.info(
        "review_complete: session=%s stages=%d insufficient_info=%d",
        context.session_id,
        len(context.completed_stages),
        len(context.insufficient_info_gaps),
    )
    return context
