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
