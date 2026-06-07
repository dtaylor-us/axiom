package com.specweaver.api.dto;

import java.math.BigDecimal;
import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Java view of the ArchInputPackage JSON produced by specweaver-agent.
 *
 * @author OpenAI
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ArchInputPackageDto(
        String packageId,
        String sessionId,
        String createdAt,
        String systemDescription,
        List<Object> requirements,
        List<GapAreaDto> gaps,
        List<ConflictItemDto> conflicts,
        List<Object> sourceDocuments,
        BigDecimal readinessScore,
        int totalRequirements,
        int highConfidenceCount,
        int inferredCount,
        int duplicateCount,
        int gapCount,
        int conflictCount
) {
}
