package com.archon.api.workshop.dto;

import java.util.List;

/**
 * The complete SEI QAW utility tree for a workshop session.
 *
 * <p>Generated when the session has at least 5 partial-or-better scenarios
 * across at least 3 quality attributes. Refreshed on every subsequent turn.</p>
 */
public record UtilityTreeDto(
        int generatedAtTurn,
        int totalScenarios,
        List<String> architecturalDrivers,
        List<UtilityTreeNodeDto> nodes,
        String generationRationale
) {}
