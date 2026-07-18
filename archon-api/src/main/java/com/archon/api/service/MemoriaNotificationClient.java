package com.archon.api.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Component
@Slf4j
public class MemoriaNotificationClient {

    private final WebClient webClient;
    private final String internalSecret;
    private final boolean enabled;
    private final Duration timeout;

    public MemoriaNotificationClient(
            WebClient.Builder webClientBuilder,
            @Value("${memoria.api.base-url:${MEMORIA_API_BASE_URL:http://memoria-api:8084}}") String baseUrl,
            @Value("${memoria.api.internal-secret:${AXIOM_INTERNAL_SECRET:}}") String internalSecret,
            @Value("${memoria.api.enabled:${MEMORIA_NOTIFICATIONS_ENABLED:true}}") boolean enabled,
            @Value("${memoria.api.timeout-seconds:${MEMORIA_API_TIMEOUT_SECONDS:5}}") int timeoutSeconds) {
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
        this.internalSecret = internalSecret == null ? "" : internalSecret;
        this.enabled = enabled;
        this.timeout = Duration.ofSeconds(timeoutSeconds);
    }

    public void notifyConversationComplete(UUID conversationId, String summary, Map<String, Object> structuredOutput) {
        if (!enabled) {
            return;
        }
        try {
            webClient.post()
                    .uri("/api/v1/memoria/sessions/ARCHON/{sessionId}/distill", conversationId)
                    .header("X-Axiom-User-Id", "system")
                    .header("X-Axiom-Internal-Secret", internalSecret)
                    .bodyValue(Map.of(
                            "pillar", "ARCHON",
                            "sessionId", conversationId.toString(),
                            "sessionSummary", summary == null ? "" : summary,
                            "sessionPayload", structuredOutput == null ? Map.of() : structuredOutput))
                    .retrieve()
                    .bodyToMono(String.class)
                    .block(timeout);
        } catch (RuntimeException ex) {
            log.warn("Memoria distillation notification failed for Archon conversation {}", conversationId, ex);
        }
    }

    public Optional<Map<String, Object>> fetchConversationContext(UUID conversationId) {
        if (!enabled) {
            return Optional.empty();
        }
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> context = webClient.get()
                    .uri("/api/v1/memoria/sessions/ARCHON/{sessionId}/context", conversationId)
                    .header("X-Axiom-User-Id", "system")
                    .header("X-Axiom-Internal-Secret", internalSecret)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block(timeout);
            return Optional.ofNullable(context);
        } catch (RuntimeException ex) {
            log.warn("Memoria context fetch failed for Archon conversation {}", conversationId, ex);
            return Optional.empty();
        }
    }
}
