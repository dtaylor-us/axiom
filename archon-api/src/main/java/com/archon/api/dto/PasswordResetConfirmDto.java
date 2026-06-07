package com.archon.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request body for completing a password reset with a token.
 *
 * @param token reset token from the emailed link
 * @param newPassword new password candidate
 * @param confirmPassword repeated password confirmation
 */
public record PasswordResetConfirmDto(
        @NotBlank
        String token,

        @NotBlank
        @Size(min = 12, message = "Password must be at least 12 characters")
        String newPassword,

        @NotBlank
        String confirmPassword
) {}
