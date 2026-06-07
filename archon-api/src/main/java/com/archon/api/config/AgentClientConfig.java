package com.archon.api.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration properties for the Agent client.
 * Maps to properties prefixed with "agent" in application configuration.
 */
@Data
@ConfigurationProperties(prefix = "agent")
public class AgentClientConfig {
    /** Base URL for the agent service */
    private String baseUrl;
    
    /** Internal secret for authentication */
    private String internalSecret;

    /** Connection timeout in seconds for opening the agent socket. */
    private int connectTimeoutSeconds = 10;

    /** Read timeout in seconds for long-running local LLM inference. */
    private int readTimeoutSeconds = 360;
    
    /** Legacy request timeout in seconds retained for older local profiles. */
    private int timeoutSeconds = 360;

    /** Circuit breaker sliding window size (default: 10 calls) */
    private int cbSlidingWindowSize = 10;

    /** Failure rate threshold percentage to open circuit (default: 50) */
    private int cbFailureRateThreshold = 50;

    /** Seconds to wait in open state before half-open probe (default: 30) */
    private int cbWaitDurationOpenState = 30;

    /** Number of calls allowed in half-open state (default: 3) */
    private int cbPermittedHalfOpen = 3;

    /** Rate limiter max calls per period (default: 20) */
    private int rlLimitForPeriod = 20;

    /** Rate limiter refresh period in seconds (default: 60) */
    private int rlLimitRefreshPeriod = 60;

    /** Rate limiter max wait for a permit in milliseconds (default: 500) */
    private int rlTimeoutMs = 500;
}
