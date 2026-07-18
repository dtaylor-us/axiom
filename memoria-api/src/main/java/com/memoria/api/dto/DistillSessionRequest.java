package com.memoria.api.dto;

import com.memoria.api.domain.model.Pillar;
import jakarta.validation.constraints.NotNull;

import java.util.Map;
import java.util.UUID;

public record DistillSessionRequest(
        UUID projectId,
        @NotNull Pillar pillar,
        @NotNull UUID sessionId,
        String sessionSummary,
        Map<String, Object> sessionPayload) {
}
