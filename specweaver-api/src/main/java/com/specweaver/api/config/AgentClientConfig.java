package com.specweaver.api.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration properties for the SpecWeaver agent client.
 */
@Data
@ConfigurationProperties(prefix = "agent")
public class AgentClientConfig {

    /** Base URL for specweaver-agent. */
    private String baseUrl;

    /** Request timeout in seconds for long-running extraction. */
    private int timeoutSeconds = 300;
}
