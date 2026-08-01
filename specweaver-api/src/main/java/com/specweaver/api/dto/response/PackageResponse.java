package com.specweaver.api.dto.response;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * API representation of a generated ArchInputPackage.
 */
public record PackageResponse(
        UUID packageId,
        UUID sessionId,
        Instant createdAt,
        BigDecimal readinessScore,
        String readinessLabel,
        String systemDescription,
        List<?> requirements,
        List<?> gaps,
        List<?> conflicts,
        List<?> sourceDocuments,
        int totalRequirements,
        int highConfidenceCount,
        int inferredCount,
        int duplicateCount,
        int gapCount,
        int conflictCount
) {

    /**
     * Derives a human-readable readiness label from the score.
     */
    public static String readinessLabel(BigDecimal score) {
        double s = score == null ? 0.0 : score.doubleValue();
        if (s >= 0.85) {
            return "Ready for architecture";
        }
        if (s >= 0.70) {
            return "Mostly ready — minor gaps";
        }
        if (s >= 0.50) {
            return "Partially ready — gaps present";
        }
        if (s >= 0.30) {
            return "Significant gaps — review needed";
        }
        return "Not ready — major gaps";
    }
}
