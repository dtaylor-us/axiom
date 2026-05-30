"""Tests for pipeline response formatter."""

import pytest
from app.models import ArchitectureContext
from app.pipeline.formatter import (
    format_response,
    _title,
    _format_item,
    _fmt_parsed,
    _fmt_challenges,
    _fmt_characteristics,
    _fmt_conflicts,
    _fmt_architecture,
    _fmt_tradeoffs,
    _fmt_adl,
    _fmt_weaknesses,
    _fmt_fmea,
    _fmt_review,
    _fmt_nested,
    _get_char_name,
)


class TestFormatResponse:
    """Tests for the main format_response function."""

    def test_empty_context_returns_header_only(self):
        ctx = ArchitectureContext(raw_requirements="test")
        result = format_response(ctx)
        assert result.startswith("# Architecture Analysis Report")
        # Should have no section headers beyond the main title
        assert "## " not in result

    def test_parsed_entities_included(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            parsed_entities={
                "functional_requirements": ["Auth", "Payments"],
                "system_name": "PaymentGateway",
            },
        )
        result = format_response(ctx)
        assert "## Parsed Requirements" in result
        assert "Auth" in result
        assert "Payments" in result
        assert "PaymentGateway" in result

    def test_challenges_section_shows_all_subsections(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            missing_requirements=[{"description": "No SLA defined"}],
            ambiguities=[{"description": "Unclear scaling needs"}],
            hidden_assumptions=[{"description": "Assumes single region"}],
            clarifying_questions=[{"description": "What is target RPS?"}],
        )
        result = format_response(ctx)
        assert "## Requirement Challenges" in result
        assert "### Missing Requirements" in result
        assert "No SLA defined" in result
        assert "### Ambiguities" in result
        assert "Unclear scaling needs" in result
        assert "### Hidden Assumptions" in result
        assert "Assumes single region" in result
        assert "### Clarifying Questions" in result
        assert "What is target RPS?" in result

    def test_scenarios_are_omitted(self):
        """Scenarios are no longer rendered in the output."""
        ctx = ArchitectureContext(
            raw_requirements="test",
            scenarios=[
                {"name": "Happy Path", "stimulus": "User pays", "response": "OK"},
            ],
        )
        result = format_response(ctx)
        assert "## Scenarios" not in result

    def test_architecture_design_nested(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            architecture_design={
                "style": "Microservices",
                "components": ["API Gateway", "Payment Service"],
            },
        )
        result = format_response(ctx)
        assert "## Architecture Design" in result
        assert "Microservices" in result
        assert "API Gateway" in result

    def test_governance_score_included(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            governance_score=85,
        )
        result = format_response(ctx)
        assert "**Governance Score**: 85/100" in result

    def test_empty_fields_are_omitted(self):
        """Only populated fields should produce sections."""
        ctx = ArchitectureContext(
            raw_requirements="test",
            trade_offs=[{"description": "Latency vs consistency"}],
        )
        result = format_response(ctx)
        assert "## Trade-off Analysis" in result
        assert "Latency vs consistency" in result
        # Empty sections should not appear
        assert "## Parsed Requirements" not in result
        assert "## Scenarios" not in result
        assert "## Architecture Design" not in result

    def test_all_analysis_sections(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            characteristics=[{"description": "High availability"}],
            characteristic_conflicts=[{"description": "Availability vs cost"}],
            adl_rules=[{"description": "Use async messaging"}],
            weaknesses=[{"description": "Single point of failure"}],
            fmea_risks=[{"description": "Database outage", "severity": "high"}],
            review_findings={"overall": "Needs improvement"},
        )
        result = format_response(ctx)
        assert "## Quality Characteristics" in result
        assert "## Characteristic Conflicts" in result
        assert "## Architecture Definition Language (ADL)" not in result
        assert "## Weakness Analysis" in result
        assert "## FMEA Risk Analysis" in result
        assert "## Architecture Review" in result


class TestTitle:
    """Tests for the _title helper."""

    def test_snake_case(self):
        assert _title("functional_requirements") == "Functional Requirements"

    def test_camel_case(self):
        assert _title("hiddenAssumptions") == "Hidden Assumptions"

    def test_single_word(self):
        assert _title("name") == "Name"


class TestFormatItem:
    """Tests for the _format_item helper."""

    def test_string_item(self):
        assert _format_item("hello") == "hello"

    def test_dict_with_description(self):
        result = _format_item({"description": "My item", "severity": "high"})
        assert "My item" in result
        assert "high" in result

    def test_dict_without_description(self):
        result = _format_item({"key": "val", "other": "data"})
        assert "val" in result
        assert "data" in result

    def test_dict_with_name(self):
        result = _format_item({"name": "Widget"})
        assert result == "Widget"


class TestFmtParsed:
    """Tests for _fmt_parsed covering all rich-data branches."""

    def test_domain_and_system_type_intro(self):
        lines = _fmt_parsed({"domain": "finance", "system_type": "platform"})
        combined = "\n".join(lines)
        assert "Finance" in combined
        assert "Platform" in combined

    def test_functional_requirements_as_dicts(self):
        fr = [{"id": "FR1", "description": "Login", "priority": "high"}]
        lines = _fmt_parsed({"functional_requirements": fr})
        combined = "\n".join(lines)
        assert "FR1" in combined
        assert "Login" in combined
        assert "HIGH" in combined

    def test_functional_requirements_as_strings(self):
        lines = _fmt_parsed({"functional_requirements": ["Login", "Logout"]})
        combined = "\n".join(lines)
        assert "Login" in combined
        assert "Logout" in combined

    def test_constraints_as_dicts(self):
        c = [{"description": "PCI-DSS required", "type": "regulatory"}]
        lines = _fmt_parsed({"constraints": c})
        combined = "\n".join(lines)
        assert "PCI-DSS required" in combined
        assert "Regulatory" in combined

    def test_constraints_as_strings(self):
        lines = _fmt_parsed({"constraints": ["Must use TLS 1.3"]})
        assert "Must use TLS 1.3" in "\n".join(lines)

    def test_integration_points_as_dicts(self):
        ip = [{"system": "Stripe", "direction": "outbound", "protocol": "REST"}]
        lines = _fmt_parsed({"integration_points": ip})
        combined = "\n".join(lines)
        assert "Stripe" in combined
        assert "Outbound" in combined
        assert "Rest" in combined

    def test_integration_points_as_strings(self):
        lines = _fmt_parsed({"integration_points": ["Stripe API"]})
        assert "Stripe API" in "\n".join(lines)

    def test_quality_signals(self):
        lines = _fmt_parsed({"quality_signals": ["availability", "latency"]})
        combined = "\n".join(lines)
        assert "`availability`" in combined

    def test_ambiguous_terms(self):
        lines = _fmt_parsed({"ambiguous_terms": ["real-time", "scalable"]})
        combined = "\n".join(lines)
        assert "`real-time`" in combined

    def test_fallback_list_key(self):
        lines = _fmt_parsed({"extra_systems": ["SystemA", "SystemB"]})
        combined = "\n".join(lines)
        assert "Extra Systems" in combined
        assert "SystemA" in combined

    def test_fallback_dict_key(self):
        lines = _fmt_parsed({"deployment_info": {"region": "us-east-1"}})
        combined = "\n".join(lines)
        assert "Deployment Info" in combined
        assert "us-east-1" in combined

    def test_fallback_scalar_key(self):
        lines = _fmt_parsed({"system_name": "PaymentGateway"})
        combined = "\n".join(lines)
        assert "PaymentGateway" in combined


class TestFmtChallenges:
    """Tests for _fmt_challenges covering area/term/assumption-rich paths."""

    def test_missing_requirements_with_area(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            missing_requirements=[{
                "area": "observability",
                "description": "No logging defined",
                "impact_if_ignored": "Blind in production",
            }],
        )
        lines = _fmt_challenges(ctx)
        combined = "\n".join(lines)
        assert "Observability" in combined
        assert "No logging defined" in combined
        assert "Impact if ignored:" in combined
        assert "Blind in production" in combined

    def test_missing_requirements_simple_list(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            missing_requirements=[{"description": "No SLA"}],
        )
        lines = _fmt_challenges(ctx)
        assert "No SLA" in "\n".join(lines)

    def test_ambiguities_with_term_table(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            ambiguities=[{
                "term": "real-time",
                "context": "latency requirement",
                "possible_interpretations": ["<100ms", "<1s"],
            }],
        )
        lines = _fmt_challenges(ctx)
        combined = "\n".join(lines)
        assert "real-time" in combined
        assert "<100ms" in combined

    def test_ambiguities_simple_list(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            ambiguities=[{"description": "Unclear RPS"}],
        )
        assert "Unclear RPS" in "\n".join(_fmt_challenges(ctx))

    def test_hidden_assumptions_with_table(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            hidden_assumptions=[{
                "assumption": "Single region deployment",
                "risk_if_wrong": "Global outage",
            }],
        )
        lines = _fmt_challenges(ctx)
        combined = "\n".join(lines)
        assert "Single region deployment" in combined
        assert "Global outage" in combined

    def test_hidden_assumptions_simple_list(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            hidden_assumptions=[{"description": "Assumes SQL"}],
        )
        assert "Assumes SQL" in "\n".join(_fmt_challenges(ctx))

    def test_clarifying_questions_with_references_and_blocks(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            clarifying_questions=[{
                "question": "What is target TPS?",
                "references": "FR-1, NFR-3",
                "blocks_decision": "architecture style selection",
            }],
        )
        lines = _fmt_challenges(ctx)
        combined = "\n".join(lines)
        assert "What is target TPS?" in combined
        assert "References:" in combined
        assert "Blocks:" in combined

    def test_clarifying_questions_plain_strings(self):
        ctx = ArchitectureContext(
            raw_requirements="test",
            clarifying_questions=[{"question": "What is peak TPS?"}],
        )
        assert "What is peak TPS?" in "\n".join(_fmt_challenges(ctx))


class TestFmtCharacteristics:
    """Tests for _fmt_characteristics with justification-rich data."""

    def test_rich_characteristics_with_justification(self):
        chars = [{
            "name": "availability",
            "justification": "99.99% uptime mandatory",
            "measurable_target": "99.99%",
            "current_requirement_coverage": "high",
            "tensions_with": ["cost", "performance"],
        }]
        lines = _fmt_characteristics(chars)
        combined = "\n".join(lines)
        assert "Availability" in combined
        assert "99.99% uptime mandatory" in combined
        assert "99.99%" in combined
        assert "cost" in combined

    def test_simple_characteristics(self):
        chars = [{"description": "High availability"}]
        lines = _fmt_characteristics(chars)
        assert "High availability" in "\n".join(lines)

    def test_get_char_name_with_name_key(self):
        assert _get_char_name({"name": "scalability"}) == "scalability"

    def test_get_char_name_with_description_fallback(self):
        assert _get_char_name({"description": "high perf"}) == "high perf"

    def test_get_char_name_with_title_fallback(self):
        assert _get_char_name({"title": "resilience"}) == "resilience"

    def test_get_char_name_empty(self):
        assert _get_char_name({}) == "—"


class TestFmtConflicts:
    """Tests for _fmt_conflicts with rich and simple data."""

    def test_rich_conflict(self):
        conflicts = [{
            "characteristic_a": "availability",
            "characteristic_b": "cost",
            "nature": "direct_trade_off",
            "explanation": "More replicas = more cost",
            "resolution_strategy": "Use spot instances",
            "priority_recommendation": "Prefer availability in critical paths",
        }]
        lines = _fmt_conflicts(conflicts)
        combined = "\n".join(lines)
        assert "Availability" in combined
        assert "Cost" in combined
        assert "More replicas = more cost" in combined
        assert "Use spot instances" in combined
        assert "Prefer availability" in combined

    def test_simple_conflict(self):
        lines = _fmt_conflicts([{"description": "Availability vs cost"}])
        assert "Availability vs cost" in "\n".join(lines)


class TestFmtArchitecture:
    """Tests for _fmt_architecture covering all nested branches."""

    def test_style_selection_with_scores(self):
        design = {
            "style_selection": {
                "style_scores": [{
                    "style": "Microservices",
                    "score": 85,
                    "driving_characteristics": ["scalability"],
                    "vetoed": False,
                    "veto_reason": None,
                }],
                "selected_style": "Microservices",
                "runner_up": "Event-Driven",
                "selection_rationale": "Best fit for scale",
            }
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "Microservices" in combined
        assert "Event-Driven" in combined
        assert "Best fit for scale" in combined

    def test_style_and_domain_intro(self):
        design = {
            "style": "Event-Driven",
            "domain": "finance",
            "system_type": "streaming",
            "rationale": "Handles async payment events",
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "Event-Driven" in combined
        assert "Finance" in combined
        assert "Handles async payment events" in combined

    def test_components_as_dicts(self):
        design = {
            "components": [{
                "name": "API Gateway",
                "type": "gateway",
                "responsibility": "Routes requests",
                "technology": "Kong",
                "technology_rationale": "Battle-tested",
                "characteristic_drivers": ["availability"],
                "exposes": ["REST"],
                "depends_on": ["Auth Service"],
            }]
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "API Gateway" in combined
        assert "Kong" in combined
        assert "Routes requests" in combined
        assert "availability" in combined

    def test_components_as_strings(self):
        design = {"components": ["API Gateway", "Payment Service"]}
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "API Gateway" in combined

    def test_interactions_as_dicts(self):
        design = {
            "interactions": [{
                "from": "Gateway",
                "to": "Auth",
                "pattern": "sync",
                "description": "Auth check",
                "rationale": "Low latency needed",
            }]
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "Gateway" in combined
        assert "Auth" in combined
        assert "Auth check" in combined

    def test_interactions_as_strings(self):
        design = {"interactions": ["Gateway -> Auth"]}
        lines = _fmt_architecture(design)
        assert "Gateway -> Auth" in "\n".join(lines)

    def test_primary_flow(self):
        design = {
            "primary_flow": {
                "description": "Happy path payment",
                "steps": [
                    {"step": 1, "component": "Gateway", "action": "Receive request"},
                    "Validate token",
                ],
            }
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "Happy path payment" in combined
        assert "Gateway" in combined
        assert "Receive request" in combined

    def test_characteristic_coverage(self):
        design = {
            "characteristic_coverage": {
                "well_addressed": ["availability"],
                "partially_addressed": ["cost"],
                "deferred": ["observability"],
            }
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "Well Addressed" in combined
        assert "availability" in combined
        assert "Partially Addressed" in combined
        assert "Deferred" in combined

    def test_when_to_reconsider(self):
        design = {"when_to_reconsider_this_style": "Traffic exceeds 100k TPS"}
        lines = _fmt_architecture(design)
        assert "Traffic exceeds 100k TPS" in "\n".join(lines)

    def test_fallback_keys_in_architecture(self):
        design = {
            "deployment_notes": {"region": "us-east-1"},
            "non_functional_tags": ["PCI-DSS", "SOC2"],
            "version": "1.0",
        }
        lines = _fmt_architecture(design)
        combined = "\n".join(lines)
        assert "us-east-1" in combined
        assert "PCI-DSS" in combined
        assert "1.0" in combined


class TestFmtTradeoffs:
    """Tests for _fmt_tradeoffs with decision_id-rich data."""

    def test_rich_tradeoff(self):
        tradeoffs = [{
            "decision_id": "TD-001",
            "decision": "Use async messaging",
            "optimises_characteristics": ["throughput", "resilience"],
            "sacrifices_characteristics": ["consistency"],
            "acceptable_because": "Eventual consistency acceptable",
            "context_dependency": "Only for non-financial flows",
            "recommendation": "Apply to notification service",
            "confidence": "high",
            "confidence_reason": "Proven pattern",
            "options_considered": [
                {"option": "Sync REST", "rejected_because": "Too slow"},
                "Polling",
            ],
        }]
        lines = _fmt_tradeoffs(tradeoffs)
        combined = "\n".join(lines)
        assert "TD-001" in combined
        assert "async messaging" in combined
        assert "throughput" in combined
        assert "consistency" in combined
        assert "Eventual consistency" in combined
        assert "Sync REST" in combined
        assert "Polling" in combined
        assert "Proven pattern" in combined

    def test_simple_tradeoff(self):
        lines = _fmt_tradeoffs([{"description": "Latency vs consistency"}])
        assert "Latency vs consistency" in "\n".join(lines)


class TestFmtAdl:
    """Tests for _fmt_adl with adl_id-rich data."""

    def test_rich_adl_hard_enforcement(self):
        rules = [{
            "adl_id": "ADL-001",
            "metadata": {
                "description": "No synchronous cross-service calls",
                "requires": "Message broker",
            },
            "adl_source": "component A -> queue -> component B",
            "characteristic_enforced": "resilience",
            "enforcement_level": "hard",
        }]
        lines = _fmt_adl(rules)
        combined = "\n".join(lines)
        assert "ADL-001" in combined
        assert "No synchronous cross-service calls" in combined
        assert "**Hard**" in combined
        assert "resilience" in combined
        assert "component A -> queue" in combined

    def test_adl_soft_enforcement(self):
        rules = [{
            "adl_id": "ADL-002",
            "metadata": {"description": "Prefer async messaging"},
            "enforcement_level": "soft",
        }]
        lines = _fmt_adl(rules)
        assert "*Soft*" in "\n".join(lines)

    def test_adl_simple_fallback(self):
        lines = _fmt_adl([{"description": "Use event sourcing"}])
        assert "Use event sourcing" in "\n".join(lines)


class TestFmtWeaknesses:
    """Tests for _fmt_weaknesses with id-based rich data."""

    def test_rich_weakness(self):
        weaknesses = [{
            "id": "W-001",
            "description": "No circuit breaker",
            "category": "resilience_gap",
            "component_affected": "Payment Service",
            "severity": 4,
            "likelihood": 3,
            "effort_to_fix": "medium",
            "early_warning_signals": ["Timeouts increasing", "Error rate spike"],
            "mitigation": "Add Resilience4j circuit breaker",
            "linked_characteristic": "resilience",
        }]
        lines = _fmt_weaknesses(weaknesses)
        combined = "\n".join(lines)
        assert "W-001" in combined
        assert "No circuit breaker" in combined
        assert "Payment Service" in combined
        assert "4/5" in combined
        assert "Timeouts increasing" in combined
        assert "Add Resilience4j" in combined

    def test_simple_weakness(self):
        lines = _fmt_weaknesses([{"description": "SPOF in DB layer"}])
        assert "SPOF in DB layer" in "\n".join(lines)


class TestFmtFmea:
    """Tests for _fmt_fmea with rpn/failure_mode data."""

    def test_rich_fmea_risk(self):
        risks = [{
            "failure_mode": "Database connection pool exhaustion",
            "rpn": 72,
            "severity": 8,
            "occurrence": 3,
            "detection": 3,
            "effect": "Service unavailability for all users",
            "recommended_action": "Implement connection pooling with PgBouncer",
        }]
        lines = _fmt_fmea(risks)
        combined = "\n".join(lines)
        assert "Database connection pool exhaustion" in combined
        assert "RPN: 72" in combined
        assert "Service unavailability" in combined
        assert "PgBouncer" in combined

    def test_fmea_simple_fallback(self):
        lines = _fmt_fmea([{"description": "Network timeout", "severity": "high"}])
        combined = "\n".join(lines)
        assert "Network timeout" in combined


class TestFmtReview:
    """Tests for _fmt_review with challenged and unchallenged paths."""

    def test_challenged_style_selection(self):
        findings = {
            "style_selection_challenge": {
                "challenged": True,
                "reason": "Top char not in driving characteristics",
                "recommended_alternative": "Event-Driven",
            }
        }
        lines = _fmt_review(findings)
        combined = "\n".join(lines)
        assert "Challenged:** Yes" in combined
        assert "Top char not in driving characteristics" in combined
        assert "Event-Driven" in combined

    def test_unchallenged_style_selection(self):
        findings = {
            "style_selection_challenge": {"challenged": False, "reason": ""}
        }
        lines = _fmt_review(findings)
        assert "well-justified" in "\n".join(lines)

    def test_other_key_as_dict(self):
        findings = {"adl_coverage": {"total": 5, "covered": 4}}
        lines = _fmt_review(findings)
        combined = "\n".join(lines)
        assert "Adl Coverage" in combined
        assert "5" in combined

    def test_other_key_as_list(self):
        findings = {"flagged_decisions": ["ADL-001", "ADL-003"]}
        lines = _fmt_review(findings)
        combined = "\n".join(lines)
        assert "Flagged Decisions" in combined
        assert "ADL-001" in combined

    def test_other_key_scalar(self):
        findings = {"overall": "Needs improvement"}
        lines = _fmt_review(findings)
        assert "Needs improvement" in "\n".join(lines)


class TestFmtNested:
    """Tests for _fmt_nested recursive helper."""

    def test_nested_dict(self):
        sections: list[str] = []
        _fmt_nested({"config": {"timeout": 30, "retries": 3}}, sections, depth=0)
        combined = "\n".join(sections)
        assert "Config" in combined
        assert "30" in combined

    def test_nested_list(self):
        sections: list[str] = []
        _fmt_nested({"tags": ["a", "b"]}, sections, depth=0)
        combined = "\n".join(sections)
        assert "Tags" in combined
        assert "a" in combined

    def test_nested_scalar(self):
        sections: list[str] = []
        _fmt_nested({"version": "1.0"}, sections, depth=0)
        assert "1.0" in "\n".join(sections)

    def test_nested_list_of_dicts(self):
        sections: list[str] = []
        _fmt_nested({"items": [{"name": "Widget"}]}, sections, depth=0)
        assert "Widget" in "\n".join(sections)
