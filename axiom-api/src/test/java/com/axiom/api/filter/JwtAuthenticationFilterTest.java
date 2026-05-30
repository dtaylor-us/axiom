package com.axiom.api.filter;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilterChain;

import reactor.core.publisher.Mono;

/**
 * Verifies JWT validation and header forwarding behavior at the gateway edge.
 */
class JwtAuthenticationFilterTest {

    private static final String JWT_SECRET = "abcdefghijklmnopqrstuvwxyz123456";

    /**
     * Valid tokens forward identity headers to downstream route processing.
     */
    @Test
    void validToken_setsForwardingHeaders() {
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(new ObjectMapper(), JWT_SECRET);
        String token = createToken("user-42", "person@example.com", 300);

        MockServerHttpRequest request = MockServerHttpRequest.get("/api/v1/archon/sessions")
                .header("Authorization", "Bearer " + token)
                .build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);

        AtomicReference<ServerWebExchange> capturedExchange = new AtomicReference<>();
        WebFilterChain chain = innerExchange -> {
            capturedExchange.set(innerExchange);
            return Mono.empty();
        };

        filter.filter(exchange, chain).block();

        assertEquals("user-42", capturedExchange.get().getRequest().getHeaders()
                .getFirst(JwtAuthenticationFilter.AXIOM_USER_ID_HEADER));
        assertEquals("person@example.com", capturedExchange.get().getRequest().getHeaders()
                .getFirst(JwtAuthenticationFilter.AXIOM_EMAIL_HEADER));
    }

    /**
     * Missing token yields 401 for protected routes.
     */
    @Test
    void missingToken_returns401() {
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(new ObjectMapper(), JWT_SECRET);

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/archon/sessions").build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
    }

    /**
     * Expired tokens yield 401.
     */
    @Test
    void expiredToken_returns401() {
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(new ObjectMapper(), JWT_SECRET);
        String token = createToken("user-42", "person@example.com", -60);

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/archon/sessions")
                        .header("Authorization", "Bearer " + token)
                        .build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
    }

    /**
     * Malformed tokens yield 401.
     */
    @Test
    void malformedToken_returns401() {
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(new ObjectMapper(), JWT_SECRET);

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/archon/sessions")
                        .header("Authorization", "Bearer malformed.token.value")
                        .build());

        filter.filter(exchange, ignored -> Mono.empty()).block();

        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
    }

    /**
     * Public auth endpoints bypass JWT checks by design.
     */
    @Test
    void publicEndpoints_bypassJwtValidation() {
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(new ObjectMapper(), JWT_SECRET);

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.method(HttpMethod.POST, "/api/v1/auth/login").build());

        AtomicBoolean chainInvoked = new AtomicBoolean(false);
        filter.filter(exchange, ignored -> {
            chainInvoked.set(true);
            return Mono.empty();
        }).block();

        assertTrue(chainInvoked.get());
        assertEquals(null, exchange.getResponse().getStatusCode());
    }

    private static String createToken(String subject, String email, long validForSeconds) {
        long now = Instant.now().getEpochSecond();
        long expiration = now + validForSeconds;

        String headerJson = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payloadJson = "{\"sub\":\"" + subject + "\",\"email\":\"" + email
                + "\",\"exp\":" + expiration + "}";

        String encodedHeader = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(headerJson.getBytes(StandardCharsets.UTF_8));
        String encodedPayload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(payloadJson.getBytes(StandardCharsets.UTF_8));
        String signingInput = encodedHeader + "." + encodedPayload;

        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(JWT_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String signature = Base64.getUrlEncoder().withoutPadding().encodeToString(
                    mac.doFinal(signingInput.getBytes(StandardCharsets.UTF_8)));
            return signingInput + "." + signature;
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to build JWT for tests", ex);
        }
    }
}
