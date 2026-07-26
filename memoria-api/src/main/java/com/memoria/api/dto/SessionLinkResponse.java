package com.memoria.api.dto;

import com.memoria.api.domain.model.Pillar;

import java.time.LocalDateTime;
import java.util.UUID;

public record SessionLinkResponse(
        UUID id,
        UUID projectId,
        Pillar pillar,
        UUID sessionId,
        LocalDateTime linkedAt) {
}
