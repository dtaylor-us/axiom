package com.memoria.api.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "memoria.agent")
public class MemoriaAgentConfig {
    private String baseUrl;
    private String internalSecret;
    private int timeoutSeconds = 120;
}
