package com.aiarchitect.api.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Data Transfer Object for authentication requests.
 * Contains user credentials and optional name information.
 */
@Data
public class AuthRequest {

    /** User email address. Must not be blank and must be a valid email format. */
    @NotBlank @Email
    private String email;

    /** User password. Must not be blank and must be between 8 and 128 characters. */
    @NotBlank @Size(min = 8, max = 128)
    private String password;

    /** Optional user name. */
    private String name;
}
