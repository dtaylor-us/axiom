package com.lens.api.domain.model;

import java.time.LocalDateTime;
import java.util.UUID;

public record ArchitectureEvidence(
    UUID id,
    UUID sessionId,
    EvidenceType evidenceType,
    String content,
    String sourceLabel,
    LocalDateTime submittedAt
) {}
