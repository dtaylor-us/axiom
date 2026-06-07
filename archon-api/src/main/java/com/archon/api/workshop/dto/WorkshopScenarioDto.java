package com.archon.api.workshop.dto;

import java.util.List;

/**
 * One operational scenario elicited during a workshop session.
 *
 * <p>Derived from {@code WorkshopContext.scenarios} in the persisted JSON.
 * {@code completeness} is computed server-side from field substance — never
 * trusted from LLM output alone.</p>
 */
public record WorkshopScenarioDto(
        String scenarioId,
        String title,
        String stimulus,
        String source,
        String environment,
        String artifact,
        String response,
        String responseMeasure,
        List<String> exercisesAttributes,
        String evidenceQuote,
        int derivedInTurn,
        String completeness
) {}
