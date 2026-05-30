package com.archon.api.config;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import io.github.resilience4j.ratelimiter.RateLimiterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Registers named Resilience4j CircuitBreaker and RateLimiter
 * instances for the agent HTTP client, driven by {@link AgentClientConfig}.
 *
 * <p>We build these programmatically rather than via YAML so that
 * the same typed config class controls all agent-related settings,
 * making the Helm values.yaml overlay simpler.</p>
 */
@Configuration
public class AgentResilienceConfig {

    /**
     * Circuit breaker protecting all outbound calls to the Python agent.
     * Opens when the failure rate exceeds the configured threshold within
     * the sliding window, preventing cascading failures.
     */
    @Bean
    public CircuitBreaker agentCircuitBreaker(AgentClientConfig config) {
        CircuitBreakerConfig cbConfig = CircuitBreakerConfig.custom()
                .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(config.getCbSlidingWindowSize())
                .failureRateThreshold(config.getCbFailureRateThreshold())
                .waitDurationInOpenState(
                        Duration.ofSeconds(config.getCbWaitDurationOpenState()))
                .permittedNumberOfCallsInHalfOpenState(
                        config.getCbPermittedHalfOpen())
                .build();

        return CircuitBreakerRegistry.of(cbConfig)
                .circuitBreaker("agentClient");
    }

    /**
     * Rate limiter preventing excessive calls to the Python agent.
     * Limits concurrent pipeline invocations to protect the LLM budget.
     */
    @Bean
    public RateLimiter agentRateLimiter(AgentClientConfig config) {
        RateLimiterConfig rlConfig = RateLimiterConfig.custom()
                .limitForPeriod(config.getRlLimitForPeriod())
                .limitRefreshPeriod(
                        Duration.ofSeconds(config.getRlLimitRefreshPeriod()))
                .timeoutDuration(
                        Duration.ofMillis(config.getRlTimeoutMs()))
                .build();

        return RateLimiterRegistry.of(rlConfig)
                .rateLimiter("agentClient");
    }
}
