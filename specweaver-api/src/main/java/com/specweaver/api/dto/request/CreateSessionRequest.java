package com.specweaver.api.dto.request;

import jakarta.validation.constraints.Size;

/**
 * Request body for creating a SpecWeaver session.
 */
public record CreateSessionRequest(
        @Size(max = 255) String title
) {}
