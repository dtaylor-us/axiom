package com.specweaver.api.service;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

/**
 * Resolves the authenticated principal into the UUID stored on sessions.
 */
@Component
public class AuthenticationUserResolver {

    /**
     * Converts the Spring Security principal name into a stable UUID.
     *
     * @param authentication authenticated request principal
     * @return user UUID
     */
    public UUID resolveUserId(Authentication authentication) {
        String principal = authentication.getName();
        try {
            return UUID.fromString(principal);
        } catch (IllegalArgumentException e) {
            return UUID.nameUUIDFromBytes(principal.getBytes(StandardCharsets.UTF_8));
        }
    }
}
