package com.archon.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Simplified token request for auto-authentication.
 * Only requires a username (no email/password).
 */
@Data
public class TokenRequest {

    /** Display name / username. Must not be blank. */
    @NotBlank @Size(max = 128)
    private String username;
}
