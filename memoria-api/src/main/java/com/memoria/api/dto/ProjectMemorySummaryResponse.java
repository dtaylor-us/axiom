package com.memoria.api.dto;

public record ProjectMemorySummaryResponse(
        long totalFacts,
        long activeFacts,
        long staleFacts,
        long archivedFacts,
        long supersededFacts,
        long decisions,
        long requirements,
        long openRisks,
        long adrCount,
        long expiringSoon) {
}
