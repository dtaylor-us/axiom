from __future__ import annotations

from app.models.contracts import ReviewContext


async def evidence_parsing(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("evidence_parsing")
    context.parsed_evidence = {"summary": "parsed"}
    return context


async def azure_waf_analysis(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("azure_waf_analysis")
    context.azure_waf_scorecard = {}
    return context


async def atam_analysis(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("atam_analysis")
    context.atam_analysis = {}
    return context


async def sei_analysis(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("sei_analysis")
    context.sei_analysis = {}
    return context


async def structural_analysis(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("structural_analysis")
    context.structural_analysis = {}
    return context


async def risk_identification(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("risk_identification")
    context.risks = []
    return context


async def recommendation_generation(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("recommendation_generation")
    context.recommendations = []
    return context


async def executive_summary(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("executive_summary")
    context.executive_summary = "Lens review complete."
    return context


async def report_assembly(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("report_assembly")
    context.review_report = {"sessionId": context.session_id, "overallRating": "APPROVED_WITH_CONDITIONS"}
    return context


async def review_complete(context: ReviewContext) -> ReviewContext:
    context.completed_stages.append("review_complete")
    return context
