package com.aiarchitect.api.workshop.dto;

import java.util.List;

/**
 * An architectural requirement derived from a workshop scenario.
 *
 * <p>Implications state what must be true about the system without naming
 * the architectural mechanism that will achieve it. Each implication traces
 * to the specific scenario that necessitates it.</p>
 */
public record ArchitectureImplicationDto(
        String implicationId,
        String sourceScenarioId,
        String sourceScenarioTitle,
        String implication,
        String tradeoff,
        List<String> affectedQualityAttrs,
        String constraintType,
        String constraintClassification,
        String strength,
        String measurableCondition
) {}
