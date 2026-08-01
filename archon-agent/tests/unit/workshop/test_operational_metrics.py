"""Tests for operational metric detection in workshop scenarios."""

from app.workshop.context import WorkshopScenario, compute_scenario_completeness


def _scenario(response_measure: str) -> WorkshopScenario:
    return WorkshopScenario(
        scenario_id="SC-1",
        stimulus="payment gateway slows during peak ordering",
        environment="production lunch rush window",
        artifact="checkout service",
        response="payment confirmation remains available to users",
        response_measure=response_measure,
    )


def test_is_operational_metric_returns_true_for_availability_target() -> None:
    assert _scenario("99.9% availability").is_operational_metric() is True


def test_is_operational_metric_returns_true_for_latency_target() -> None:
    assert _scenario("under 300ms").is_operational_metric() is True


def test_is_operational_metric_returns_true_for_throughput_target() -> None:
    assert _scenario("500 requests/second").is_operational_metric() is True


def test_is_operational_metric_returns_false_for_cancellation_rate() -> None:
    assert _scenario("reduced cancellation rate").is_operational_metric() is False


def test_is_operational_metric_returns_false_for_customer_satisfaction() -> None:
    assert _scenario("improved customer satisfaction").is_operational_metric() is False


def test_compute_completeness_requires_operational_metric() -> None:
    completeness = compute_scenario_completeness(
        "payment gateway slows during peak ordering",
        "production lunch rush window",
        "payment confirmation remains available to users",
        "reduced cancellation rate",
    )

    assert completeness == "needs_operational_metric"


def test_compute_completeness_returns_complete_for_operational_metric() -> None:
    completeness = compute_scenario_completeness(
        "payment gateway slows during peak ordering",
        "production lunch rush window",
        "payment confirmation remains available to users",
        "payment confirmation under 300ms",
    )

    assert completeness == "complete"
