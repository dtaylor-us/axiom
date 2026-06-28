package com.lens.api.service;

import com.lens.api.exception.BadRequestException;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Component
public class AuthenticationUserResolver {

    public UUID resolveUserId(Authentication authentication, String userIdHeader) {
        String rawUserId = userIdHeader;
        if (rawUserId == null || rawUserId.isBlank()) {
            if (authentication == null || authentication.getName() == null || authentication.getName().isBlank()) {
                throw new BadRequestException("Missing user identity. Provide X-Axiom-User-Id or Authorization token.");
            }
            rawUserId = authentication.getName();
        }

        try {
            return UUID.fromString(rawUserId);
        } catch (IllegalArgumentException ignored) {
            return UUID.nameUUIDFromBytes(rawUserId.getBytes(StandardCharsets.UTF_8));
        }
    }
}
