package com.lens.api.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record ReviewSession(
    UUID id,
    UUID userId,
    String title,
    String systemDescription,
    ReviewStatus status,
    int gapRound,
    boolean gapsResolved,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}
