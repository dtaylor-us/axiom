package com.aiarchitect.api.client;

import java.time.Duration;

import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import io.github.resilience4j.reactor.circuitbreaker.operator.CircuitBreakerOperator;
import io.github.resilience4j.reactor.ratelimiter.operator.RateLimiterOperator;
import io.micrometer.observation.ObservationRegistry;
import io.netty.channel.ChannelOption;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.netty.http.client.HttpClient;

import com.aiarchitect.api.config.AgentClientConfig;
import com.aiarchitect.api.dto.AgentRequest;
import com.aiarchitect.api.exception.AgentCommunicationException;

/**
 * HTTP client for communicating with the AI Agent service.
 * Handles streaming responses from the agent using Spring WebClient.
 *
 * <p>The WebClient is built with Micrometer observation so that
 * W3C TraceContext headers (traceparent / tracestate) propagate
 * automatically to the Python agent, enabling cross-service traces
 * visible in Jaeger.</p>
 *
 * <p>All outbound calls are protected by a Resilience4j circuit breaker
 * and rate limiter. When the circuit opens, callers receive an
 * {@link AgentCommunicationException} immediately instead of waiting
 * for the agent to time out.</p>
 */
@Component
@Slf4j
public class AgentHttpClient {

    private final WebClient webClient;
    private final AgentClientConfig config;
    private final CircuitBreaker circuitBreaker;
    private final RateLimiter rateLimiter;

    /**
     * Initializes the HTTP client with configuration, tracing, and resilience.
     *
     * @param config              the agent client configuration
     * @param observationRegistry Micrometer observation registry for trace propagation
     * @param circuitBreaker      Resilience4j circuit breaker for the agent
     * @param rateLimiter         Resilience4j rate limiter for the agent
     */
    public AgentHttpClient(AgentClientConfig config,
                           ObservationRegistry observationRegistry,
                           CircuitBreaker circuitBreaker,
                           RateLimiter rateLimiter) {
        this.config = config;
        this.circuitBreaker = circuitBreaker;
        this.rateLimiter = rateLimiter;
        HttpClient httpClient = HttpClient.create()
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS,
                        config.getConnectTimeoutSeconds() * 1000)
                .responseTimeout(Duration.ofSeconds(config.getReadTimeoutSeconds()));
        this.webClient = WebClient.builder()
                .baseUrl(config.getBaseUrl())
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .defaultHeader(HttpHeaders.CONTENT_TYPE,
                               MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader("X-Internal-Secret", config.getInternalSecret())
                .codecs(c -> c.defaultCodecs()
                              .maxInMemorySize(10 * 1024 * 1024))
                .observationRegistry(observationRegistry)
                .build();
    }

    /**
     * Streams responses from the agent service.
     *
     * <p>The Flux is wrapped with a rate limiter (applied first to
     * reject excess requests quickly) and a circuit breaker (applied
     * second to stop calls when the agent is unhealthy).</p>
     *
     * @param request the agent request
     * @return a Flux of response strings
     */
    public Flux<String> stream(AgentRequest request) {
        return webClient.post()
                .uri("/agent/stream")
                .bodyValue(request)
                .retrieve()
                .onStatus(HttpStatusCode::isError, response ->
                        response.bodyToMono(String.class).map(body ->
                                new AgentCommunicationException(
                                    "Agent error " + response.statusCode()
                                    + ": " + body)))
                .bodyToFlux(String.class)
                .timeout(Duration.ofSeconds(config.getReadTimeoutSeconds()))
                .filter(line -> !line.isBlank())
                .transformDeferred(RateLimiterOperator.of(rateLimiter))
                .transformDeferred(CircuitBreakerOperator.of(circuitBreaker))
                .doOnError(CallNotPermittedException.class,
                        e -> log.warn("Agent circuit breaker OPEN — request rejected"))
                .doOnError(RequestNotPermitted.class,
                        e -> log.warn("Agent rate limiter — request rejected"))
                .doOnError(e -> {
                    if (!(e instanceof CallNotPermittedException)
                            && !(e instanceof RequestNotPermitted)) {
                        log.error("Agent stream error", e);
                    }
                });
    }
}
