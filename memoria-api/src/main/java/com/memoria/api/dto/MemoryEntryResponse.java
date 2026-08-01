package com.memoria.api.dto;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;

import java.time.LocalDateTime;
import java.util.UUID;

public record MemoryEntryResponse(
        UUID id,
        UUID projectId,
        MemoryType memoryType,
        MemoryTier tier,
        String content,
        String rationale,
        Pillar sourcePillar,
        UUID sourceSessionId,
        String sourceExcerpt,
        MemoryConfidence confidence,
        MemoryStatus status,
        UUID supersededBy,
        LocalDateTime expiresAt,
        LocalDateTime lastAccessedAt,
        int accessCount,
        String[] tags,
        LocalDateTime createdAt,
        LocalDateTime updatedAt) {
}
