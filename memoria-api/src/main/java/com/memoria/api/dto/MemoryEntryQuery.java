package com.memoria.api.dto;

import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;

import java.time.LocalDateTime;

public record MemoryEntryQuery(
        MemoryStatus status,
        MemoryType memoryType,
        MemoryTier tier,
        Pillar sourcePillar,
        String tag,
        LocalDateTime createdAfter,
        LocalDateTime createdBefore,
        LocalDateTime expiresBefore,
        String q) {
}
