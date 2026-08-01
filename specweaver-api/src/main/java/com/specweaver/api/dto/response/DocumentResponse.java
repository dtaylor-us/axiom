package com.specweaver.api.dto.response;

import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.DocumentType;

import java.time.Instant;
import java.util.UUID;

/**
 * API representation of a session document.
 */
public record DocumentResponse(
        UUID id,
        DocumentType documentType,
        String filename,
        String sourceLabel,
        String storageKey,
        String extractedText,
        DocumentStatus status,
        String errorMessage,
        Instant createdAt,
        Instant processedAt
) {}
