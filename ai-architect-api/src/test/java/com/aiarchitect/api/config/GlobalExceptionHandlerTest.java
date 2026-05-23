package com.aiarchitect.api.config;

import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.*;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleValidation_returnsBadRequest() {
        // Validation handler is tested via integration tests (400 scenarios).
        // This tests the IllegalArgumentException handler directly.
        ProblemDetail pd = handler.handleIllegalArgument(
                new IllegalArgumentException("bad input"));
        assertEquals(HttpStatus.BAD_REQUEST.value(), pd.getStatus());
        assertEquals("bad input", pd.getDetail());
    }

    @Test
    void handleMessageNotReadable_returnsBadRequestForMalformedJson() {
        HttpMessageNotReadableException ex = new HttpMessageNotReadableException(
                "JSON parse error: Unexpected character");
        ProblemDetail pd = handler.handleMessageNotReadable(ex);
        assertEquals(HttpStatus.BAD_REQUEST.value(), pd.getStatus());
        assertTrue(pd.getDetail().contains("Malformed request body"));
    }

    @Test
    void handleResponseStatus_returnsMatchingStatusCode() {
        ResponseStatusException ex = new ResponseStatusException(
                HttpStatus.NOT_FOUND, "not found");
        ProblemDetail pd = handler.handleResponseStatus(ex);
        assertEquals(HttpStatus.NOT_FOUND.value(), pd.getStatus());
    }

    @Test
    void handleResponseStatus_handlesNullReason() {
        ResponseStatusException ex = new ResponseStatusException(
                HttpStatus.CONFLICT);
        ProblemDetail pd = handler.handleResponseStatus(ex);
        assertEquals(HttpStatus.CONFLICT.value(), pd.getStatus());
        assertNotNull(pd.getDetail());
    }

    @Test
    void handleAll_returnsInternalServerError() {
        ProblemDetail pd = handler.handleAll(new RuntimeException("boom"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR.value(), pd.getStatus());
        assertEquals("An unexpected error occurred. Please try again.",
                pd.getDetail());
    }

    // ── Circuit Breaker / Rate Limiter handlers ─────────────────

    @Test
    void handleCircuitBreakerOpen_returns503() {
        // Create a real CallNotPermittedException via the Resilience4j API
        CircuitBreaker cb = CircuitBreakerRegistry.of(
                CircuitBreakerConfig.custom()
                        .slidingWindowSize(1)
                        .minimumNumberOfCalls(1)
                        .failureRateThreshold(100)
                        .build()
        ).circuitBreaker("test-cb");

        // Force the circuit breaker open
        cb.transitionToOpenState();

        CallNotPermittedException ex = CallNotPermittedException
                .createCallNotPermittedException(cb);

        ProblemDetail pd = handler.handleCircuitBreakerOpen(ex);
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE.value(), pd.getStatus());
        assertTrue(pd.getDetail().contains("temporarily unavailable"));
    }

    @Test
    void handleRateLimited_returns429() {
        RateLimiter rl = RateLimiterRegistry.of(
                RateLimiterConfig.custom()
                        .limitForPeriod(1)
                        .build()
        ).rateLimiter("test-rl");

        RequestNotPermitted ex = RequestNotPermitted.createRequestNotPermitted(rl);

        ProblemDetail pd = handler.handleRateLimited(ex);
        assertEquals(HttpStatus.TOO_MANY_REQUESTS.value(), pd.getStatus());
        assertTrue(pd.getDetail().contains("Too many requests"));
    }
}
