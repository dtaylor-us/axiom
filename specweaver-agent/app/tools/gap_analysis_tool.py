"""Domain-aware missing requirement detection for SpecWeaver Phase 1b."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import Counter

from app.llm.client import LLMCallException
from app.llm.schemas import SCHEMAS
from app.models.contracts import (
    ClassifiedRequirementSet,
    GapAnalysisResult,
    GapArea,
    GapSeverity,
)
from app.pipeline.context import SpecWeaverContext
from app.prompts import load_prompt
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

MAX_DOMAIN_GAPS = 5
SEVERITY_VALUES = ("critical", "high", "medium", "low")

CHECKLIST_GAPS = [
    {
        "area": "Performance requirements",
        "keywords": [
            "performance",
            "latency",
            "throughput",
            "response time",
            "concurrent",
            "tps",
            "rps",
        ],
        "severity": "high",
        "explanation": (
            "Without explicit performance targets, the architecture cannot "
            "make informed decisions about caching, database selection, or "
            "infrastructure sizing."
        ),
        "clarification_question": (
            "What are the expected response times under normal load? What is "
            "the peak concurrent user count or transaction volume?"
        ),
        "affected_categories": ["non_functional"],
    },
    {
        "area": "Availability and uptime expectations",
        "keywords": [
            "availability",
            "uptime",
            "sla",
            "99",
            "downtime",
            "failover",
            "redundancy",
        ],
        "severity": "high",
        "explanation": (
            "Availability targets drive decisions about redundancy, deployment "
            "topology, and disaster recovery."
        ),
        "clarification_question": (
            "What is the required availability SLA? Is there a maintenance "
            "window? What is the acceptable recovery time objective?"
        ),
        "affected_categories": ["non_functional"],
    },
    {
        "area": "Data retention and archival policy",
        "keywords": [
            "retention",
            "archive",
            "purge",
            "delete",
            "history",
            "data lifecycle",
            "years",
            "months",
        ],
        "severity": "high",
        "explanation": (
            "Data retention policy affects storage architecture, compliance "
            "posture, and database design."
        ),
        "clarification_question": (
            "How long must data be retained? Are there regulatory requirements "
            "driving the retention period? How should data be archived or purged?"
        ),
        "affected_categories": ["data_considerations", "constraints"],
    },
    {
        "area": "Authentication and authorisation model",
        "keywords": [
            "auth",
            "login",
            "sso",
            "role",
            "permission",
            "access control",
            "identity",
            "user management",
        ],
        "severity": "critical",
        "explanation": (
            "Authentication and authorisation are foundational security "
            "requirements. Their absence leaves the security architecture "
            "undefined."
        ),
        "clarification_question": (
            "How will users authenticate? Is SSO required? What is the role "
            "and permission model?"
        ),
        "affected_categories": ["functional", "constraints"],
    },
    {
        "area": "Audit and compliance logging",
        "keywords": [
            "audit",
            "log",
            "compliance",
            "trail",
            "history",
            "traceability",
            "immutable",
        ],
        "severity": "medium",
        "explanation": (
            "Audit logging requirements affect database design and may require "
            "an append-only event store pattern."
        ),
        "clarification_question": (
            "What user actions must be audited? How long must audit logs be "
            "retained? Must audit logs be immutable?"
        ),
        "affected_categories": ["non_functional", "data_considerations"],
    },
    {
        "area": "Scalability and growth expectations",
        "keywords": [
            "scale",
            "growth",
            "users",
            "volume",
            "elastic",
            "horizontal",
            "vertical",
        ],
        "severity": "medium",
        "explanation": (
            "Scalability expectations determine whether the architecture needs "
            "horizontal scaling capability or whether a single-server approach "
            "is acceptable."
        ),
        "clarification_question": (
            "What is the expected user/data growth over 12-24 months? Must the "
            "system scale horizontally or is vertical scaling acceptable?"
        ),
        "affected_categories": ["non_functional"],
    },
    {
        "area": "Failure handling and recovery",
        "keywords": [
            "failure",
            "error",
            "exception",
            "recovery",
            "retry",
            "circuit",
            "fallback",
            "degraded",
        ],
        "severity": "medium",
        "explanation": (
            "Failure handling requirements affect resilience patterns, error UX "
            "design, and monitoring strategy."
        ),
        "clarification_question": (
            "How should the system behave when a downstream dependency fails? "
            "What is acceptable degraded-mode behaviour?"
        ),
        "affected_categories": ["non_functional"],
    },
    {
        "area": "Deployment and operational environment",
        "keywords": [
            "deploy",
            "cloud",
            "azure",
            "aws",
            "gcp",
            "kubernetes",
            "docker",
            "on-premise",
            "hybrid",
        ],
        "severity": "medium",
        "explanation": (
            "Deployment constraints affect technology selection, cost, and "
            "operational model."
        ),
        "clarification_question": (
            "Where must the system be deployed? Are there cloud provider "
            "constraints? What is the target operational model?"
        ),
        "affected_categories": ["constraints"],
    },
    {
        "area": "Monitoring and observability",
        "keywords": [
            "monitor",
            "alert",
            "metric",
            "trace",
            "log",
            "observ",
            "dashboard",
            "health",
        ],
        "severity": "low",
        "explanation": (
            "Observability requirements affect the choice of monitoring stack "
            "and instrumentation approach."
        ),
        "clarification_question": (
            "What monitoring and alerting is required? Are there existing "
            "monitoring tools to integrate with?"
        ),
        "affected_categories": ["non_functional"],
    },
    {
        "area": "Integration error handling",
        "keywords": [],
        "severity": "medium",
        "explanation": (
            "When integrations are required, error handling for integration "
            "failures must be specified."
        ),
        "clarification_question": (
            "How should the system handle failures in external integrations? "
            "Is eventual consistency acceptable or must integration calls be "
            "synchronous and reliable?"
        ),
        "affected_categories": ["integrations"],
        "only_if_category_present": "integrations",
    },
]


class GapAnalysisTool(BaseTool):
    """Find missing requirement areas using checklist and LLM passes."""

    async def run(self, context: SpecWeaverContext) -> SpecWeaverContext:
        """Run checklist analysis before adding domain-specific LLM gaps."""
        started_at = time.monotonic()
        if not context.classified_requirements:
            logger.warning(
                "gap_analysis: no classified requirements. session=%s",
                context.session_id,
            )
            context.completed_stages.append("gap_analysis")
            logger.info(
                "gap_analysis: duration_ms=%d session=%s",
                int((time.monotonic() - started_at) * 1000),
                context.session_id,
            )
            return context

        checklist_gaps = self._run_checklist(context.classified_requirements)
        llm_gaps = await self._run_llm_analysis(
            context.session_id,
            context.classified_requirements,
        )
        gaps = self._merge_gaps(checklist_gaps, llm_gaps)
        by_severity = Counter(str(gap.severity) for gap in gaps)

        context.gap_analysis_result = GapAnalysisResult(
            session_id=context.session_id,
            gaps=gaps,
            gap_count=len(gaps),
            by_severity={
                severity: by_severity.get(severity, 0)
                for severity in SEVERITY_VALUES
            },
        )
        logger.info(
            "gap_analysis: found %d gaps session=%s",
            len(gaps),
            context.session_id,
        )
        context.completed_stages.append("gap_analysis")
        logger.info(
            "gap_analysis: duration_ms=%d session=%s",
            int((time.monotonic() - started_at) * 1000),
            context.session_id,
        )
        return context

    def _run_checklist(
        self,
        classified: ClassifiedRequirementSet,
    ) -> list[GapArea]:
        """Check classified requirements against common architecture gaps."""
        all_statements = " ".join(
            requirement.statement.lower()
            for requirement in classified.requirements
        )
        present_categories = {
            self._enum_value(requirement.category)
            for requirement in classified.requirements
        }

        gaps: list[GapArea] = []
        for item in CHECKLIST_GAPS:
            only_if_category = item.get("only_if_category_present")
            if only_if_category and only_if_category not in present_categories:
                continue

            keywords = item.get("keywords", [])
            if keywords and any(keyword in all_statements for keyword in keywords):
                continue

            gaps.append(
                GapArea(
                    gap_id=f"GAP-{str(uuid.uuid4())[:8]}",
                    area=str(item["area"]),
                    severity=GapSeverity(str(item["severity"])),
                    explanation=str(item["explanation"]),
                    clarification_question=str(item["clarification_question"]),
                    affected_categories=list(item["affected_categories"]),
                )
            )

        return gaps

    async def _run_llm_analysis(
        self,
        session_id: str,
        classified: ClassifiedRequirementSet,
    ) -> list[GapArea]:
        """Ask the LLM for domain-specific gaps not covered by the checklist."""
        prompt = load_prompt(
            "gap_analysis",
            session_id=session_id,
            requirements_by_category=self._group_by_category(classified),
            total_count=classified.total_count,
        )

        try:
            raw = await self.llm_client.complete(
                prompt,
                output_schema=SCHEMAS["gap_analysis"],
                schema_name="gap_analysis",
                stage_name="gap_analysis",
            )
            parsed = json.loads(raw)
        except (json.JSONDecodeError, KeyError, LLMCallException, ValueError) as exc:
            logger.warning(
                "gap_analysis: LLM pass failed. Checklist results only. "
                "error=%s session=%s",
                str(exc),
                session_id,
            )
            return []

        return [
            GapArea(
                gap_id=f"GAP-{str(uuid.uuid4())[:8]}",
                area=str(gap.get("area", "")),
                severity=GapSeverity(str(gap.get("severity", "medium"))),
                explanation=str(gap.get("explanation", "")),
                clarification_question=str(
                    gap.get("clarification_question", "")
                ),
                affected_categories=list(gap.get("affected_categories", [])),
            )
            for gap in parsed.get("gaps", [])[:MAX_DOMAIN_GAPS]
            if gap.get("area")
        ]

    def _merge_gaps(
        self,
        checklist: list[GapArea],
        llm_gaps: list[GapArea],
    ) -> list[GapArea]:
        """Merge gaps from both passes, deduplicating by area label."""
        seen_areas = {gap.area.lower() for gap in checklist}
        merged = list(checklist)

        for gap in llm_gaps:
            if gap.area.lower() in seen_areas:
                continue
            merged.append(gap)
            seen_areas.add(gap.area.lower())

        return merged

    def _group_by_category(
        self,
        classified: ClassifiedRequirementSet,
    ) -> dict[str, list[str]]:
        """Group requirement statements by classification category."""
        groups: dict[str, list[str]] = {}
        for requirement in classified.requirements:
            groups.setdefault(self._enum_value(requirement.category), []).append(
                requirement.statement
            )
        return groups

    @staticmethod
    def _enum_value(value) -> str:
        """Return the serialized value for enums or already-normalized strings."""
        return str(getattr(value, "value", value))
