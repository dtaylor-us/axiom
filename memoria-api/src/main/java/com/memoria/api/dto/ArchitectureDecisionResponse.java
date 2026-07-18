package com.memoria.api.dto;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.Pillar;

import java.time.LocalDateTime;
import java.util.UUID;

public record ArchitectureDecisionResponse(
        UUID id,
        UUID projectId,
        int adrNumber,
        String title,
        AdrStatus status,
        String context,
        String decision,
        String consequences,
        String alternativesConsidered,
        Pillar sourcePillar,
        UUID sourceSessionId,
        Integer supersededByAdrNumber,
        LocalDateTime createdAt) {
}
