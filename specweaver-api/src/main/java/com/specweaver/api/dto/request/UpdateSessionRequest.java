package com.specweaver.api.dto.request;

import jakarta.validation.constraints.Size;

/**
 * Request body for updating mutable SpecWeaver session fields.
 */
public record UpdateSessionRequest(
        @Size(max = 255) String title
) {}
