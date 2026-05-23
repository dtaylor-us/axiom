package com.aiarchitect.api.workshop.dto;

import java.util.List;

/**
 * Honest readiness assessment for on-demand attribute generation.
 */
public record GenerationReadinessDto(
        /** insufficient | partial | adequate | strong */
        String overallReadiness,
        /** Plain English: what will the output look like? */
        String confidenceNote,
        List<AttributePreviewDto> attributePreview,
        List<HighValueGapDto> highValueGaps,
        List<String> missingDomains,
        boolean canProduceUsefulOutput
) {}
