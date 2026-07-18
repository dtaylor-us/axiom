package com.memoria.api.dto;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record CreateMemoryEntryRequest(
        @NotNull MemoryType memoryType,
        @NotNull MemoryTier tier,
        @NotBlank String content,
        String rationale,
        Pillar sourcePillar,
        UUID sourceSessionId,
        String sourceExcerpt,
        MemoryConfidence confidence,
        String[] tags) {
}
