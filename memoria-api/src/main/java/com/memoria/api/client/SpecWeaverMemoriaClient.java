package com.memoria.api.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Component
@Slf4j
public class SpecWeaverMemoriaClient {

    private static final Duration TIMEOUT = Duration.ofSeconds(30);
    private static final String AXIOM_USER_ID_HEADER = "X-Axiom-User-Id";
    private static final String AXIOM_INTERNAL_SECRET_HEADER = "X-Axiom-Internal-Secret";

    private final WebClient webClient;
    private final String internalSecret;

    public SpecWeaverMemoriaClient(
            WebClient.Builder webClientBuilder,
            @Value("${specweaver.api.base-url:http://specweaver-api:8082}") String baseUrl,
            @Value("${axiom.gateway.internal-secret:}") String internalSecret) {
        this.internalSecret = internalSecret == null ? "" : internalSecret;
        this.webClient = webClientBuilder
                .baseUrl(baseUrl)
                .build();
    }

    public Optional<Map<String, Object>> getSessionPackage(UUID sessionId) {
        try {
            Map<String, Object> response = webClient.get()
                    .uri("/api/v1/sessions/{sessionId}/package", sessionId)
                    .headers(this::applyForwardedHeaders)
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

    private void applyForwardedHeaders(HttpHeaders headers) {
        if (!internalSecret.isBlank()) {
            headers.set(AXIOM_INTERNAL_SECRET_HEADER, internalSecret);
        }
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attrs == null) {
            return;
        }
        String authorization = attrs.getRequest().getHeader(HttpHeaders.AUTHORIZATION);
        if (authorization != null && !authorization.isBlank()) {
            headers.set(HttpHeaders.AUTHORIZATION, authorization);
        }
        String userId = attrs.getRequest().getHeader(AXIOM_USER_ID_HEADER);
        if (userId != null && !userId.isBlank()) {
            headers.set(AXIOM_USER_ID_HEADER, userId);
        }
    }
}
