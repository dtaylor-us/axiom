from app.models.contracts import DistillRequest
from app.pipeline.distiller import distill


async def test_distill_extracts_structured_candidates():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="ARCHON",
            session_payload={
                "decisions": [
                    {
                        "decision": "Use PostgreSQL for order consistency",
                        "rationale": "Transactional consistency is required",
                        "confidence": "HIGH",
                        "tags": ["database", "orders"],
                    }
                ]
            },
        )
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].memory_type == "DECISION"
    assert response.candidates[0].confidence == "HIGH"


async def test_distill_flags_replacement_conflict():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="SPECWEAVER",
            session_summary="Requirement: Use Azure SQL instead of PostgreSQL for order storage.",
            existing_entries=[
                {
                    "id": "00000000-0000-0000-0000-000000000003",
                    "memoryType": "REQUIREMENT",
                    "content": "Use PostgreSQL for order storage.",
                    "tags": ["orders"],
                }
            ],
        )
    )

    assert response.conflicts
    assert response.conflicts[0].existing_entry_id == "00000000-0000-0000-0000-000000000003"
    assert response.conflicts[0].supersedes is True


async def test_distill_uses_explicit_decision_label_over_requirements_hint():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="SPECWEAVER",
            session_payload={"requirements": ["Decision: Use Redis for caching."]},
        )
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].memory_type == "DECISION"
    assert response.candidates[0].content == "Use Redis for caching."


async def test_distill_uses_explicit_requirement_label_over_decisions_hint():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="ARCHON",
            session_payload={"decisions": ["Requirement: System must scale to 10k users."]},
        )
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].memory_type == "REQUIREMENT"
    assert response.candidates[0].content == "System must scale to 10k users."


async def test_distill_keeps_requirements_hint_when_no_explicit_label():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="SPECWEAVER",
            session_payload={"requirements": ["System must support 10k users."]},
        )
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].memory_type == "REQUIREMENT"
    assert response.candidates[0].content == "System must support 10k users."


async def test_distill_defaults_memory_type_when_structured_value_has_no_hint_or_keywords():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="LENS",
            session_payload={
                "analysis": {
                    "content": "Neteru Path platform overview for stakeholders.",
                    "details": "Architecture narrative without explicit type keywords.",
                }
            },
        )
    )

    assert len(response.candidates) == 1
    assert response.candidates[0].memory_type == "SESSION_SUMMARY"


async def test_distill_extracts_real_archon_architecture_shape_without_llm():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="ARCHON",
            session_payload={
                "style": "Event-driven microservices",
                "components": [
                    {
                        "name": "Order Service",
                        "responsibility": "Owns the order lifecycle and order state transitions.",
                    }
                ],
                "tradeOffs": [
                    {
                        "decision": "Use asynchronous events between bounded contexts",
                        "rationale": "Reduces runtime coupling between services.",
                    }
                ],
                "fmeaRisks": [
                    {
                        "description": "Duplicate event delivery can repeat side effects.",
                        "mitigation": "Use idempotency keys in every consumer.",
                    }
                ],
            },
        )
    )

    assert [(candidate.memory_type, candidate.content) for candidate in response.candidates] == [
        ("DECISION", "Order Service"),
        ("DECISION", "Use asynchronous events between bounded contexts"),
        ("RISK", "Duplicate event delivery can repeat side effects."),
    ]


async def test_distill_extracts_real_specweaver_package_shape_without_llm():
    response = await distill(
        DistillRequest(
            session_id="00000000-0000-0000-0000-000000000001",
            project_id="00000000-0000-0000-0000-000000000002",
            pillar="SPECWEAVER",
            session_payload={
                "systemDescription": "A payment platform for marketplace settlements.",
                "requirements": [
                    {
                        "statement": "Settlement processing must complete within two hours.",
                        "confidence": "HIGH",
                        "sourceExcerpts": ["settlements complete within two hours"],
                    }
                ],
                "gaps": [
                    {
                        "description": "The retention period has not been specified.",
                        "severity": "HIGH",
                    }
                ],
            },
        )
    )

    assert [(candidate.memory_type, candidate.content) for candidate in response.candidates] == [
        ("SESSION_SUMMARY", "A payment platform for marketplace settlements."),
        ("REQUIREMENT", "Settlement processing must complete within two hours."),
        ("RISK", "The retention period has not been specified."),
    ]
