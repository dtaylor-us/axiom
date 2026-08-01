package com.archon.api.client;

import com.archon.api.config.AgentClientConfig;
import com.archon.api.dto.AgentRequest;
import com.archon.api.exception.AgentCommunicationException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import io.micrometer.observation.ObservationRegistry;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

import java.io.IOException;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.*;

class AgentHttpClientTest {

    private MockWebServer mockServer;
    private AgentHttpClient agentHttpClient;
    private CircuitBreaker circuitBreaker;
    private RateLimiter rateLimiter;

    @BeforeEach
    void setUp() throws IOException {
        mockServer = new MockWebServer();
        mockServer.start();

        AgentClientConfig config = new AgentClientConfig();
        config.setBaseUrl(mockServer.url("/").toString());
        config.setInternalSecret("test-secret");
        config.setTimeoutSeconds(5);

        // Permissive defaults for most tests
        circuitBreaker = CircuitBreakerRegistry.of(
                CircuitBreakerConfig.custom()
                        .slidingWindowSize(10)
                        .failureRateThreshold(50)
                        .waitDurationInOpenState(Duration.ofSeconds(30))
                        .permittedNumberOfCallsInHalfOpenState(3)
                        .build()
        ).circuitBreaker("test");

        rateLimiter = RateLimiterRegistry.of(
                RateLimiterConfig.custom()
                        .limitForPeriod(100)
                        .limitRefreshPeriod(Duration.ofSeconds(1))
                        .timeoutDuration(Duration.ofMillis(500))
                        .build()
        ).rateLimiter("test");

        agentHttpClient = new AgentHttpClient(
                config,
                ObservationRegistry.create(),
                circuitBreaker,
                rateLimiter);
    }

    @AfterEach
    void tearDown() throws IOException {
        mockServer.shutdown();
    }

    @Test
    void stream_returnsNdjsonLinesForValidResponse() {
        String body = "{\"type\":\"CHUNK\",\"content\":\"hello\"}\n"
                    + "{\"type\":\"COMPLETE\",\"conversationId\":\"c1\"}\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/x-ndjson")
                .setBody(body));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentHttpClient.stream(request))
                .assertNext(line -> assertTrue(line.contains("CHUNK")))
                .assertNext(line -> assertTrue(line.contains("COMPLETE")))
                .verifyComplete();
    }

    @Test
    void stream_emitsErrorForServerError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(500)
                .setBody("Internal Server Error"));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentHttpClient.stream(request))
                .expectErrorMatches(e ->
                        e instanceof AgentCommunicationException
                        && e.getMessage().contains("Agent error"))
                .verify();
    }

    @Test
    void stream_filtersBlankLines() {
        String body = "{\"type\":\"CHUNK\",\"content\":\"data\"}\n\n\n";
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/x-ndjson")
                .setBody(body));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentHttpClient.stream(request))
                .assertNext(line -> assertTrue(line.contains("CHUNK")))
                .verifyComplete();
    }

    @Test
    void stream_sendsInternalSecretHeader() throws Exception {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/x-ndjson")
                .setBody("{\"type\":\"COMPLETE\"}\n"));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentHttpClient.stream(request)).expectNextCount(1)
                .verifyComplete();

        var recordedRequest = mockServer.takeRequest();
        assertEquals("test-secret", recordedRequest.getHeader("X-Internal-Secret"));
        assertEquals("/agent/stream", recordedRequest.getPath());
    }

    // ── Circuit Breaker Tests ───────────────────────────────────

    @Test
    void stream_circuitBreakerOpensAfterFailures() {
        // Create a strict circuit breaker: opens after 3 failures in a window of 3
        CircuitBreaker strictCb = CircuitBreakerRegistry.of(
                CircuitBreakerConfig.custom()
                        .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                        .slidingWindowSize(3)
                        .minimumNumberOfCalls(3)
                        .failureRateThreshold(100)
                        .waitDurationInOpenState(Duration.ofSeconds(60))
                        .build()
        ).circuitBreaker("strict-test");

        AgentClientConfig config = new AgentClientConfig();
        config.setBaseUrl(mockServer.url("/").toString());
        config.setInternalSecret("test-secret");
        config.setTimeoutSeconds(5);

        AgentHttpClient strictClient = new AgentHttpClient(
                config, ObservationRegistry.create(), strictCb, rateLimiter);

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        // Enqueue 3 failures to trip the breaker
        for (int i = 0; i < 3; i++) {
            mockServer.enqueue(new MockResponse()
                    .setResponseCode(500)
                    .setBody("fail"));
        }

        // Consume the 3 failures
        for (int i = 0; i < 3; i++) {
            StepVerifier.create(strictClient.stream(request))
                    .expectError()
                    .verify();
        }

        // Circuit should now be OPEN — verify state
        assertEquals(CircuitBreaker.State.OPEN, strictCb.getState());
    }

    // ── Rate Limiter Tests ──────────────────────────────────────

    @Test
    void stream_rateLimiterAllowsRequestsWithinLimit() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/x-ndjson")
                .setBody("{\"type\":\"COMPLETE\"}\n"));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        // With a limit of 100/s, a single request should succeed
        StepVerifier.create(agentHttpClient.stream(request))
                .expectNextCount(1)
                .verifyComplete();
    }
}
