package com.lens.api.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record GapQuestion(
    UUID id,
    UUID sessionId,
    int round,
    GapCategory category,
    String question,
    String rationale,
    boolean answered,
    String answer,
    boolean skipped,
    LocalDateTime askedAt,
    LocalDateTime answeredAt
) {}
