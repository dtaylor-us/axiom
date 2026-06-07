package com.specweaver.api.dto.request;

import com.specweaver.api.domain.model.DocumentType;
import jakarta.validation.constraints.NotNull;

/**
 * Request metadata for document ingestion.
 */
public record IngestDocumentRequest(
        String text,
        @NotNull DocumentType documentType,
        String sourceLabel
) {}
