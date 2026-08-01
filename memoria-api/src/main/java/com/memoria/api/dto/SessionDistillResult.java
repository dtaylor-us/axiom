package com.memoria.api.dto;

import java.util.UUID;

public record SessionDistillResult(
        UUID sessionId,
        String pillar,
        String status,
        int candidates,
        int persisted,
        int superseded,
        int conflicts,
        String error) {
}
