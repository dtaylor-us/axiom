package com.archon.api.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for authentication response.
 * Contains authentication token and user email.
 */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class AuthResponse {
    /** JWT or authentication token */
    private String token;
    
    /** User email address */
    private String email;
}
