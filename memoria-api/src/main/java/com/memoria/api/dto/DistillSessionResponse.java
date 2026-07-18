package com.memoria.api.dto;

import java.util.List;
import java.util.UUID;

public record DistillSessionResponse(
        UUID projectId,
        UUID sessionId,
        int candidatesReceived,
        int entriesCreated,
        int entriesSuperseded,
        List<MemoryEntryResponse> createdEntries,
        String message) {
}
