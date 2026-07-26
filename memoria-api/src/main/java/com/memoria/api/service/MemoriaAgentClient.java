package com.memoria.api.service;

import com.memoria.api.config.MemoriaAgentConfig;
import com.memoria.api.dto.AgentDistillRequest;
import com.memoria.api.dto.AgentDistillResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientException;

import java.time.Duration;

@Component
@RequiredArgsConstructor
@Slf4j
public class MemoriaAgentClient {

    private final WebClient.Builder webClientBuilder;
    private final MemoriaAgentConfig config;

    public AgentDistillResponse distill(AgentDistillRequest request) {
        log.info("DIAG agent-call: url={}/distill pillar={} sessionId={} payloadKeys={}",
                config.getBaseUrl(), request.pillar(), request.sessionId(),
                request.sessionPayload() != null ? request.sessionPayload().keySet() : "null");
        try {
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
        } catch (WebClientException | IllegalStateException ex) {
            log.error("DIAG agent-call-FAILED: pillar={} sessionId={} error={} cause={}",
                    request.pillar(), request.sessionId(), ex.getClass().getSimpleName(), ex.getMessage());
            return null;
        }
    }
}
