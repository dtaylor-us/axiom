package com.memoria.api.dto;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;

import java.time.LocalDateTime;
import java.util.UUID;

public record ContextMemoryItem(
        UUID id,
        MemoryType memoryType,
        String content,
        String rationale,
        Pillar sourcePillar,
        UUID sourceSessionId,
        String sourceExcerpt,
        MemoryConfidence confidence,
        LocalDateTime expiresAt,
        String[] tags,
        LocalDateTime createdAt) {
}
