package com.memoria.api.dto;

import com.memoria.api.domain.model.Pillar;
import jakarta.validation.constraints.NotBlank;

import java.util.UUID;

public record CreateAdrRequest(
        @NotBlank String title,
        @NotBlank String context,
        @NotBlank String decision,
        String consequences,
        String alternativesConsidered,
        Pillar sourcePillar,
        UUID sourceSessionId) {
}
