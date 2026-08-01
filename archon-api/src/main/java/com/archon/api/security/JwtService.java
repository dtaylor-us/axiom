package com.archon.api.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;

/**
 * Service for generating, validating, and extracting information from JWT tokens.
 */
@Service
@Slf4j
public class JwtService {

    // HMAC signing key derived from the secret
    private final SecretKey signingKey;
    // Token expiration time in milliseconds
    private final long expirationMs;

    /**
     * Constructor that initializes the signing key and expiration time from configuration.
     *
     * @param secret the secret key from application properties
     * @param expirationMs the token expiration time (default: 86400000ms = 24 hours)
     */
    public JwtService(
            @Value("${security.jwt.secret:super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes}") String secret,
            @Value("${security.jwt.expiration-ms:86400000}") long expirationMs) {
        this.signingKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expirationMs = expirationMs;
    }

    /**
     * Generate a JWT token for the given user identifier (email).
     *
     * @param subject the user identifier (typically an email)
     * @return the signed JWT token as a string
     */
    public String generateToken(String subject) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(subject)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusMillis(expirationMs)))
                .signWith(signingKey)
                .compact();
    }

    /**
     * Extract the subject (email) from a valid token.
     *
     * @param token the JWT token to parse
     * @return the subject, or null if the token is invalid / expired
     */
    public String extractSubject(String token) {
        try {
            // Parse and verify the token signature
            Claims claims = Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
            return claims.getSubject();
        } catch (JwtException | IllegalArgumentException e) {
            // Log and return null for any JWT validation errors
            log.debug("Invalid JWT: {}", e.getMessage());
            return null;
        }
    }

    /**
     * Validate the token and check it is not expired.
     *
     * @param token the JWT token to validate
     * @return true if the token is valid and not expired, false otherwise
     */
    public boolean isValid(String token) {
        return extractSubject(token) != null;
    }
}
