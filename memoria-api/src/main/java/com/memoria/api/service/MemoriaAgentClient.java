package com.memoria.api.service;

import com.memoria.api.config.MemoriaAgentConfig;
import com.memoria.api.dto.AgentDistillRequest;
import com.memoria.api.dto.AgentDistillResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;

@Component
@RequiredArgsConstructor
public class MemoriaAgentClient {

    private final WebClient.Builder webClientBuilder;
    private final MemoriaAgentConfig config;

    public AgentDistillResponse distill(AgentDistillRequest request) {
        return webClientBuilder
                .baseUrl(config.getBaseUrl())
                .build()
                .post()
                .uri("/distill")
                .header("X-Internal-Secret", config.getInternalSecret() == null ? "" : config.getInternalSecret())
                .bodyValue(request)
                .retrieve()
                .bodyToMono(AgentDistillResponse.class)
                .block(Duration.ofSeconds(config.getTimeoutSeconds()));
    }
}
