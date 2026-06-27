from app.pipeline.graph import ORDERED_STAGES


def test_ordered_stages_has_10_entries():
    assert len(ORDERED_STAGES) == 10
