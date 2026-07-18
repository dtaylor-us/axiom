package com.specweaver.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

@Component
@Slf4j
public class MemoriaNotificationClient {

    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final String internalSecret;
    private final boolean enabled;
    private final Duration timeout;

    public MemoriaNotificationClient(
            WebClient.Builder webClientBuilder,
            ObjectMapper objectMapper,
            @Value("${memoria.api.base-url:${MEMORIA_API_BASE_URL:http://memoria-api:8084}}") String baseUrl,
            @Value("${memoria.api.internal-secret:${AXIOM_INTERNAL_SECRET:}}") String internalSecret,
            @Value("${memoria.api.enabled:${MEMORIA_NOTIFICATIONS_ENABLED:true}}") boolean enabled,
            @Value("${memoria.api.timeout-seconds:${MEMORIA_API_TIMEOUT_SECONDS:5}}") int timeoutSeconds) {
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
        this.objectMapper = objectMapper;
        this.internalSecret = internalSecret == null ? "" : internalSecret;
        this.enabled = enabled;
        this.timeout = Duration.ofSeconds(timeoutSeconds);
    }

    public void notifySessionReady(UUID sessionId, String summary, Map<String, Object> payload) {
        if (!enabled) {
            return;
        }
        try {
            webClient.post()
                    .uri("/api/v1/memoria/sessions/SPECWEAVER/{sessionId}/distill", sessionId)
                    .header("X-Axiom-User-Id", "system")
                    .header("X-Axiom-Internal-Secret", internalSecret)
                    .bodyValue(Map.of(
                            "pillar", "SPECWEAVER",
                            "sessionId", sessionId.toString(),
                            "sessionSummary", summary == null ? "" : summary,
                            "sessionPayload", payload == null ? Map.of() : payload))
                    .retrieve()
                    .bodyToMono(String.class)
                    .block(timeout);
        } catch (RuntimeException ex) {
            log.warn("Memoria distillation notification failed for SpecWeaver session {}", sessionId, ex);
        }
    }

    public Map<String, Object> parsePayload(String json) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(json, Map.class);
            return payload;
        } catch (Exception ex) {
            return Map.of("package_json", json);
        }
    }
}
