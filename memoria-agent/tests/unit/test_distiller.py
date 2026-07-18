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
