package com.memoria.api.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public record DistillationJobResponse(
        UUID id,
        UUID projectId,
        String status,
        int sessionCount,
        int totalCandidates,
        int totalPersisted,
        int totalSuperseded,
        int totalConflicts,
        List<SessionDistillResult> sessionResults,
        LocalDateTime createdAt,
        LocalDateTime completedAt) {
}
