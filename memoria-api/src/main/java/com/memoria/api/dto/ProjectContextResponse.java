package com.memoria.api.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public record ProjectContextResponse(
        UUID projectId,
        LocalDateTime assembledAt,
        List<ContextMemoryItem> decisions,
        List<ContextMemoryItem> requirements,
        List<ContextMemoryItem> constraints,
        List<ContextMemoryItem> risks,
        List<ContextMemoryItem> qualityScores,
        List<ContextAdrItem> adrs,
        ContextOmittedCounts omittedCounts) {
}
