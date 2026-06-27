"""LangGraph node functions for the Lens 10-stage review pipeline.

Each function represents one pipeline stage. Core stages abort the pipeline
on failure. Supporting stages record a gap and continue so the user always
receives a partial report rather than a blank result.

Core stages (abort on failure): evidence_parsing, risk_identification,
    report_assembly.
Supporting stages (gap recorded, pipeline continues): all others.
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

    Extracts architecture style, components, integration points,
    deployment model, and stated quality attribute concerns.
    Never invents facts — marks unknown fields explicitly.
    CORE stage: failure aborts the pipeline.
    """
    evidence_text = _format_evidence(context)
    prompt = f"""You are an expert software architect. Parse the following architecture
evidence into a structured representation.

Evidence:
{evidence_text}

Return a JSON object:
{{
  "architecture_style": "e.g. microservices, monolith, event-driven, or UNKNOWN",
  "components": [
    {{"name": "component name", "responsibility": "what it does"}}
  ],
  "integration_points": [
    {{"name": "integration name", "protocol": "e.g. REST, gRPC, message queue"}}
  ],
  "deployment_model": "e.g. Kubernetes, serverless, VMs, or UNKNOWN",
  "technology_stack": ["list of technologies mentioned"],
  "stated_quality_concerns": ["any quality attributes explicitly mentioned"],
  "stated_constraints": ["any constraints explicitly mentioned"],
  "unknown_areas": ["areas with no evidence — do not guess"]
}}

Only extract what is explicitly stated or strongly inferable from the evidence.
Mark anything not evidenced as UNKNOWN.
"""
    result = await _llm_json(prompt, "evidence_parsing")
    context.parsed_evidence = result
    context.completed_stages.append("evidence_parsing")
    logger.info("evidence_parsing: completed components=%d", len(result.get("components", [])))
    return context


# ─── Stage 2: azure_waf_analysis (SUPPORTING) ───────────────────────────────

async def azure_waf_analysis(context: ReviewContext) -> ReviewContext:
    """
    Evaluate the architecture against the five Azure Well-Architected
    Framework pillars.

    Scores each pillar 0-5 based on evidence coverage only.
    Does not assume compliance — no evidence means a gap, not a pass.
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

For each pillar, assess coverage based ONLY on the evidence provided.
Do NOT assume compliance. If there is no evidence for an area, it is a gap.

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
      "addressed": ["list of concerns that are evidenced"],
      "gaps": ["list of concerns with no evidence"],
      "findings": ["specific observations"],
      "insufficient_info": false
    }},
    "security": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": true }},
    "cost_optimisation": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }},
    "operational_excellence": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }},
    "performance_efficiency": {{ "score": 0, "addressed": [], "gaps": [], "findings": [], "insufficient_info": false }}
  }},
  "overall_waf_summary": "Brief overall assessment."
}}

Scoring guide: 0=no evidence, 1=minimal, 2=partial, 3=adequate, 4=good, 5=comprehensive.
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

Apply ATAM analysis:
1. Identify quality attribute scenarios (what the system must do under specific
   conditions to satisfy a quality attribute)
2. Identify the architecture approach that addresses each scenario
3. Identify sensitivity points (decisions with strong effect on one quality attribute)
4. Identify tradeoffs (decisions affecting multiple quality attributes oppositely)
5. Identify risks (quality attribute scenarios not supported by any architecture approach)

Mark findings as low_confidence when evidence is thin.

Return a JSON object:
{{
  "quality_attribute_scenarios": [
    {{
      "quality_attribute": "Availability",
      "scenario": "System must recover from a service failure within 30 seconds",
      "architecture_approach": "Health checks and pod restart via Kubernetes",
      "supported": true,
      "confidence": "medium"
    }}
  ],
  "sensitivity_points": [
    {{"decision": "REST communication between services", "affected_attribute": "Performance", "effect": "Synchronous coupling increases latency under load"}}
  ],
  "tradeoffs": [
    {{"decision": "Microservices decomposition", "gains": "Modifiability, Scalability", "costs": "Operational complexity, Network latency"}}
  ],
  "risks": [
    {{"quality_attribute": "Security", "scenario": "Service-to-service auth not defined", "severity": "HIGH"}}
  ],
  "atam_summary": "Brief ATAM assessment summary."
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

For each of the five SEI quality attributes, assess what tactics are evidenced
in the architecture and what is missing.

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
      "tactics_present": ["list of evidenced tactics"],
      "tactics_missing": ["list of expected but missing tactics"],
      "observations": "brief assessment"
    }},
    "performance": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "availability": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "security": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}},
    "integrability": {{"rating": "NO_EVIDENCE", "tactics_present": [], "tactics_missing": [], "observations": ""}}
  }},
  "sei_summary": "Brief SEI assessment summary."
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
    prompt = f"""You are an expert software architect assessing structural health.

Architecture Evidence:
{evidence_text}

Parsed Components:
{json.dumps(parsed.get('components', []), indent=2)}

Evaluate four structural dimensions, each scored 0-5:

- Coupling (5=very low): Are component boundaries well-defined? Are there circular
  dependencies? Are integration points contracts or direct access?
- Cohesion (5=high): Do components have single clear responsibilities? God components?
  Domain logic separated from infrastructure?
- Dependency Direction (5=clean): Do dependencies flow consistently? Inversions of
  expected dependency flow?
- Boundary Clarity (5=clear): Are service/component boundaries explicitly described?
  Is data and behaviour ownership clear? Are cross-boundary communication patterns defined?

Return a JSON object:
{{
  "coupling": {{
    "score": 3,
    "observations": ["specific observations"]
  }},
  "cohesion": {{"score": 3, "observations": []}},
  "dependency_direction": {{"score": 3, "observations": []}},
  "boundary_clarity": {{"score": 3, "observations": []}},
  "structural_summary": "Brief structural assessment."
}}

Base your assessment only on what is described in the evidence.
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

Synthesise these findings into a unified risk register. Consolidate related risks
(do not create duplicate risks for the same underlying problem). Include risks for
unresolved information gaps (severity based on what could not be evaluated).

Maximum {MAX_RISKS} risks. Order by severity descending.
Severity options: CRITICAL, HIGH, MEDIUM, LOW
Likelihood options: HIGH, MEDIUM, LOW

Return a JSON object:
{{
  "risks": [
    {{
      "title": "No authentication model defined",
      "description": "The architecture has no described authentication mechanism for user or service-to-service communication.",
      "severity": "HIGH",
      "likelihood": "HIGH",
      "affected_area": "Security",
      "mitigation_strategy": "Define and implement an IAM model covering user auth and service-to-service auth before production.",
      "framework_reference": "Azure WAF - Security"
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

Each recommendation must be SPECIFIC and ACTIONABLE.
Bad: "Improve security."
Good: "Define and document an IAM model covering service-to-service authentication
using mutual TLS or a service mesh identity system."

Return a JSON object:
{{
  "recommendations": [
    {{
      "title": "Define IAM model for service-to-service authentication",
      "description": "Implement mutual TLS or a service mesh identity system to authenticate inter-service calls. Document the auth model covering all service boundaries.",
      "priority": "P1",
      "effort": "WEEKS",
      "addresses_risk": "No authentication model defined"
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

    prompt = f"""Write a 3-5 paragraph executive summary of an architecture review
for a technical leadership audience.

Top Risks:
{json.dumps(risks, indent=2)}

Top Recommendations:
{json.dumps(recommendations, indent=2)}

Insufficient Information Areas:
{json.dumps(info_gaps, indent=2)}

The summary must include:
1. What was reviewed (brief system description)
2. Overall assessment and rating rationale
3. Top 3 risks with brief explanation
4. Top 3 recommendations
5. Any significant limitations due to insufficient information

Overall rating options:
- APPROVED: all five Azure WAF pillars addressed, no critical risks
- APPROVED_WITH_CONDITIONS: minor gaps, specific conditions documented
- NEEDS_REWORK: one or more pillars significantly unaddressed, or HIGH/CRITICAL risks
- NOT_APPROVED: critical structural failures or critical risks requiring architectural changes

System description:
{context.system_description}

Return a JSON object:
{{
  "executive_summary": "3-5 paragraph summary text...",
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
        "report_assembly: completed rating=%s risks=%d recommendations=%d gaps=%d",
        context.overall_rating,
        len(context.risks),
        len(context.recommendations),
        len(insufficient_findings),
    )
    return context


# ─── Stage 10: review_complete ───────────────────────────────────────────────

async def review_complete(context: ReviewContext) -> ReviewContext:
    """
    Final stage — marks the review as complete.

    In production this stage triggers the SSE COMPLETE event.
    """
    context.completed_stages.append("review_complete")
    logger.info(
        "review_complete: session=%s stages=%d",
        context.session_id,
        len(context.completed_stages),
    )
    return context
