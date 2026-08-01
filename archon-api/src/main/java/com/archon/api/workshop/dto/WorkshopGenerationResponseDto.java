package com.archon.api.workshop.dto;

import java.util.List;
import java.util.UUID;

/**
 * Response from POST .../generate — structured generation result plus persisted attributes.
 */
public record WorkshopGenerationResponseDto(
        UUID sessionId,
        int generationCount,
        String overallReadiness,
        String confidenceNote,
        int attributesGenerated,
        List<AttributePreviewDto> attributePreview,
        List<HighValueGapDto> highValueGaps,
        List<String> missingDomains,
        String generationSummary,
        List<QualityAttributeDto> attributes,
        boolean canContinueRefining,
        String continuationPrompt,
        boolean attributesStale
) {}
