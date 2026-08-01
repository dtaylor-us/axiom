package com.archon.api.dto;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Snapshot of the most recent pipeline run for a conversation.
 */
public record PipelineStatusResponse(
        UUID runId,
        String status,
        String lastStageCompleted,
        List<String> completedStages,
        String activeStage,
        List<EventDto> events,
        Integer governanceScore,
        Boolean hasGaps
) {

    /**
     * Persisted pipeline event projected for UI reconstruction.
     */
    public record EventDto(
            String type,
            String stage,
            Integer sequenceNum,
            Instant emittedAt,
            String payload
    ) {
    }
}
