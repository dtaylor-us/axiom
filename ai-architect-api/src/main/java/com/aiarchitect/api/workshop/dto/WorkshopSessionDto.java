package com.aiarchitect.api.workshop.dto;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Read-only summary of one workshop session.
 *
 * <p>Returned by GET /api/v1/workshop/sessions/{id} and the
 * list endpoint. Contains aggregate counts for gap and attribute
 * progress so the UI can render the progress tracker without
 * parsing context_json.</p>
 */
public record WorkshopSessionDto(
        UUID sessionId,
        String systemName,
        String workshopPhase,
        int turnCount,
        int totalGaps,
        int filledGaps,
        /** Open gaps with partial resolution progress (confidence ≥ 0.5). */
        int inProgressGaps,
        int gapCompletionPct,
        int attributeCount,
        int confirmedAttributeCount,
        boolean isComplete,
        boolean hasSufficientAttributes,
        boolean readyForPipeline,
        List<WorkshopTurnResponseDto.OpenGapDto> openGaps,
        Instant createdAt,
        Instant lastUpdated,
        /** User-triggered generation count from WorkshopContext.generation_count. */
        int generationCount,
        /** True when new turns arrived after the last generation. */
        boolean attributesStale
) {}
