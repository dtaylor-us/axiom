package com.memoria.api.dto;

import com.memoria.api.domain.model.MemoryStatus;

public record UpdateMemoryEntryRequest(
        String content,
        String rationale,
        String[] tags,
        MemoryStatus status) {
}
