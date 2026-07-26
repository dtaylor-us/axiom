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
 * Fetches SpecWeaver session package for Memoria distillation.
 *
 * <p>Uses X-Axiom-Internal-Secret for service-to-service auth.
 * Does NOT use RequestContextHolder — that fails in batch threads.</p>
 *
 * <p>The SpecWeaver package endpoint is GET /api/v1/sessions/{id}/package.
 * This endpoint returns 404 if the package has not been generated yet.
 * In that case we attempt to trigger generation first via the POST endpoint,
 * then fetch the result.</p>
 */
@Component
@Slf4j
public class SpecWeaverMemoriaClient {

    private static final Duration TIMEOUT = Duration.ofSeconds(30);
    private static final String INTERNAL_SECRET_HEADER = "X-Axiom-Internal-Secret";

    private final WebClient webClient;
    private final String internalSecret;

    public SpecWeaverMemoriaClient(
            WebClient.Builder webClientBuilder,
            @Value("${specweaver.api.base-url:http://specweaver-api:8082}") String baseUrl,
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.internalSecret = internalSecret == null ? "" : internalSecret;
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
    }

    /**
     * Fetches the requirements package for a SpecWeaver session.
     *
     * <p>First attempts GET. If 404 (not yet generated), attempts POST /generate
     * then retries GET once. If either call fails, returns empty.</p>
     *
     * @param sessionId the SpecWeaver session UUID
     * @return the package map, or empty if unavailable
     */
    public Optional<Map<String, Object>> getSessionPackage(UUID sessionId) {
        Optional<Map<String, Object>> result = fetchPackage(sessionId);
        if (result.isPresent()) {
            return result;
        }
        // Package not generated yet — trigger generation then retry
        log.info("SpecWeaverMemoriaClient: package not found, triggering generation sessionId={}",
                sessionId);
        triggerGeneration(sessionId);
        return fetchPackage(sessionId);
    }

    private Optional<Map<String, Object>> fetchPackage(UUID sessionId) {
        try {
            Map<String, Object> response = webClient.get()
                    .uri("/api/v1/sessions/{sessionId}/package", sessionId)
                    .headers(this::applyInternalHeaders)
                    .retrieve()
                    .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {})
                    .block(TIMEOUT);
            if (response == null || response.isEmpty()) {
                return Optional.empty();
            }
            log.debug("SpecWeaverMemoriaClient: fetched package sessionId={} keys={}",
                    sessionId, response.keySet());
            return Optional.of(response);
        } catch (Exception ex) {
            log.warn("SpecWeaverMemoriaClient.fetchPackage failed sessionId={} error={}",
                    sessionId, ex.getMessage());
            return Optional.empty();
        }
    }

    private void triggerGeneration(UUID sessionId) {
        try {
            webClient.post()
                    .uri("/api/v1/sessions/{sessionId}/package/generate", sessionId)
                    .headers(this::applyInternalHeaders)
                    .retrieve()
                    .bodyToMono(Void.class)
                    .block(TIMEOUT);
        } catch (Exception ex) {
            log.warn("SpecWeaverMemoriaClient.triggerGeneration failed sessionId={} error={}",
                    sessionId, ex.getMessage());
        }
    }

    private void applyInternalHeaders(HttpHeaders headers) {
        if (!internalSecret.isBlank()) {
            headers.set(INTERNAL_SECRET_HEADER, internalSecret);
        }
    }
}
