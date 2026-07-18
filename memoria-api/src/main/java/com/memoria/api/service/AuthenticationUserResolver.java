package com.memoria.api.service;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Component
public class AuthenticationUserResolver {

    public UUID resolveUserId(Authentication authentication) {
        if (authentication == null || authentication.getName() == null) {
            return UUID.nameUUIDFromBytes("local-dev".getBytes(StandardCharsets.UTF_8));
        }
        String principal = authentication.getName();
        try {
            return UUID.fromString(principal);
        } catch (IllegalArgumentException e) {
            return UUID.nameUUIDFromBytes(principal.getBytes(StandardCharsets.UTF_8));
        }
    }
}
