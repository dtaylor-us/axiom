package com.archon.api.dto;

import java.time.Instant;
import java.util.UUID;

/**
 * Status summary for the most recent pipeline run for a conversation.
 */
public record PipelineRunStatusDto(
        UUID runId,
        UUID conversationId,
        String status,
        String lastStageCompleted,
        Instant startedAt,
        Instant completedAt,
        Integer governanceScore,
        String governanceConfidence,
        Boolean hasGaps,
        String gapSummary,
        String errorStage,
        String errorMessage,
        int eventCount
) {}

