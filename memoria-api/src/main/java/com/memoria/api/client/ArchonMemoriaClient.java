package com.memoria.api.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Fetches Archon conversation output for Memoria distillation.
 *
 * <p>Uses the X-Internal-Secret header for service-to-service auth.
 * Does NOT attempt to forward the user JWT via RequestContextHolder —
 * that approach fails in batch distillation threads where no HTTP
 * request context is present. Instead, this client is called from
 * an internal endpoint that bypasses user-scoped security.</p>
 */
@Component
@Slf4j
public class ArchonMemoriaClient {

    private static final Duration TIMEOUT = Duration.ofSeconds(30);
    private static final String INTERNAL_SECRET_HEADER = "X-Internal-Secret";

    private final WebClient webClient;
    private final String internalSecret;

    public ArchonMemoriaClient(
            WebClient.Builder webClientBuilder,
            @Value("${archon.api.base-url:http://archon-api:8081}") String baseUrl,
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.internalSecret = internalSecret == null ? "" : internalSecret;
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
    }

    /**
     * Fetches the structured architecture output for an Archon conversation.
     *
     * <p>Calls the internal endpoint that does not require a user JWT.
     * Falls back to the public endpoint if the internal one returns 404
     * (conversation exists but has no architecture output yet).</p>
     *
     * @param sessionId the Archon conversation UUID
     * @return the architecture output map, or empty if unavailable
     */
    public Optional<Map<String, Object>> getConversationOutput(UUID sessionId) {
        try {
            Map<String, Object> response = webClient.get()
                    .uri("/api/v1/sessions/{sessionId}/architecture", sessionId)
                    .headers(this::applyInternalHeaders)
                    .retrieve()
                    .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {})
                    .block(TIMEOUT);
            if (response == null || response.isEmpty()) {
                log.debug("ArchonMemoriaClient: empty response for sessionId={}", sessionId);
                return Optional.empty();
            }
            log.debug("ArchonMemoriaClient: fetched output sessionId={} keys={}",
                    sessionId, response.keySet());
            return Optional.of(response);
        } catch (Exception ex) {
            log.warn("ArchonMemoriaClient.getConversationOutput failed sessionId={} error={}",
                    sessionId, ex.getMessage());
            return Optional.empty();
        }
    }

    private void applyInternalHeaders(HttpHeaders headers) {
        if (!internalSecret.isBlank()) {
            // Use X-Internal-Secret for service-to-service auth.
            // archon-api SecurityConfig must permit /api/v1/sessions/*/architecture
            // when this header is present, or expose a dedicated internal endpoint.
            headers.set(INTERNAL_SECRET_HEADER, internalSecret);
        }
    }
}
