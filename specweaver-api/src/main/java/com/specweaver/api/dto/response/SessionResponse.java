package com.specweaver.api.dto.response;

import com.specweaver.api.domain.model.SessionStatus;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * API representation of a SpecWeaver session.
 */
public record SessionResponse(
        UUID id,
        UUID userId,
        String title,
        SessionStatus status,
        Instant createdAt,
        Instant updatedAt,
        UUID archonConversationId,
        List<DocumentResponse> documents
) {}
