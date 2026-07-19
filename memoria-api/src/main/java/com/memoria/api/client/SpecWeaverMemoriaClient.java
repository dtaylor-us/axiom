package com.memoria.api.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Component
@Slf4j
public class SpecWeaverMemoriaClient {

    private static final Duration TIMEOUT = Duration.ofSeconds(30);

    private final WebClient webClient;

    public SpecWeaverMemoriaClient(
            WebClient.Builder webClientBuilder,
            @Value("${specweaver.api.base-url:http://specweaver-api:8082}") String baseUrl,
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.webClient = webClientBuilder
                .baseUrl(baseUrl)
                .defaultHeader("X-Internal-Secret", internalSecret == null ? "" : internalSecret)
                .build();
    }

    public Optional<Map<String, Object>> getSessionPackage(UUID sessionId) {
        try {
            Map<String, Object> response = webClient.get()
                    .uri("/api/v1/specweaver/sessions/{sessionId}/package/export", sessionId)
                    .retrieve()
                    .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {})
                    .block(TIMEOUT);
            return Optional.ofNullable(response);
        } catch (Exception ex) {
            log.warn("SpecWeaverMemoriaClient.getSessionPackage failed sessionId={} error={}",
                    sessionId, ex.getMessage());
            return Optional.empty();
        }
    }
}
