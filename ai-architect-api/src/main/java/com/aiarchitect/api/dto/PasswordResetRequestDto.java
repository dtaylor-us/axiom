package com.aiarchitect.api.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

/**
 * Request body for initiating a password reset email.
 *
 * @param email email address to send the reset link to
 */
public record PasswordResetRequestDto(
        @NotBlank @Email
        String email
) {}
