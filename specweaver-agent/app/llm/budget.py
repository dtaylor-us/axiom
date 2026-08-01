"""Stage-level output budgets for SpecWeaver LLM calls."""

STAGE_OUTPUT_BUDGET = {
    "extraction": 3000,
    "classification": 4000,
    "output_formatting": 2000,
}


def output_budget_for_stage(stage_name: str, fallback: int) -> int:
    """
    Return the configured output budget for a stage.

    Args:
        stage_name: Pipeline stage name.
        fallback: Provider-calculated fallback budget.

    Returns:
        Stage budget when configured, otherwise fallback.
    """
    return STAGE_OUTPUT_BUDGET.get(stage_name, fallback)
