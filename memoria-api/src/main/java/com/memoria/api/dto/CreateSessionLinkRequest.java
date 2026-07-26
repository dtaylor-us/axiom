package com.memoria.api.dto;

import com.memoria.api.domain.model.Pillar;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record CreateSessionLinkRequest(
        @NotNull Pillar pillar,
        @NotNull UUID sessionId) {
}
