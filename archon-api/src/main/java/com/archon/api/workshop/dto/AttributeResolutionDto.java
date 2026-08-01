package com.archon.api.workshop.dto;

import java.util.List;

/**
 * Resolution traceability slice for one workshop attribute.
 */
public record AttributeResolutionDto(
        String attributeId,
        String attributeName,
        List<ResolvedAnswerDto> resolvedAnswers,
        List<String> openQuestions,
        int resolvedCount,
        int openCount
) {}
