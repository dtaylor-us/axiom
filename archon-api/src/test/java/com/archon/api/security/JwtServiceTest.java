package com.archon.api.security;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;

import static org.junit.jupiter.api.Assertions.*;

class JwtServiceTest {

    private static final String SECRET = "test-secret-key-that-is-at-least-32-bytes-long!!";
    private static final long EXPIRATION_MS = 86_400_000L;

    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        jwtService = new JwtService(SECRET, EXPIRATION_MS);
    }

    @Test
    void generateToken_producesNonBlankString() {
        String token = jwtService.generateToken("alice@test.com");
        assertNotNull(token);
        assertFalse(token.isBlank());
    }

    @Test
    void extractSubject_returnsUsernameUsedToGenerate() {
        String token = jwtService.generateToken("bob@test.com");
        String subject = jwtService.extractSubject(token);
        assertEquals("bob@test.com", subject);
    }

    @Test
    void isValid_returnsFalseForExpiredToken() {
        // Create a service with a very short expiration (already expired)
        JwtService expired = new JwtService(SECRET, -1000L);
        String token = expired.generateToken("charlie@test.com");
        assertFalse(expired.isValid(token));
    }

    @Test
    void isValid_returnsFalseForTamperedToken() {
        String token = jwtService.generateToken("dave@test.com");
        // Tamper with the token by changing a character in the signature
        String tampered = token.substring(0, token.length() - 2) + "XX";
        assertFalse(jwtService.isValid(tampered));
    }

    @Test
    void extractSubject_returnsNullForTokenSignedWithDifferentKey() {
        SecretKey otherKey = Keys.hmacShaKeyFor(
                "another-secret-key-also-at-least-32-bytes-long!!"
                        .getBytes(StandardCharsets.UTF_8));
        String foreignToken = Jwts.builder()
                .subject("eve@test.com")
                .issuedAt(Date.from(Instant.now()))
                .expiration(Date.from(Instant.now().plusMillis(EXPIRATION_MS)))
                .signWith(otherKey)
                .compact();
        assertNull(jwtService.extractSubject(foreignToken));
    }
}
