from app.pipeline.graph import ORDERED_STAGES
from app.models.contracts import ReviewContext


def test_ordered_stages_has_10_entries():
    assert len(ORDERED_STAGES) == 10


def test_review_context_accepts_project_memory_context():
    context = ReviewContext(
        session_id="s1",
        system_description="A system with enough detail.",
        evidence=[],
        project_memory_context={"adrs": [{"title": "Use eventing"}]},
    )

    assert context.project_memory_context["adrs"][0]["title"] == "Use eventing"
