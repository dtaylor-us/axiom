package com.memoria.api.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Fetches Archon conversation output for Memoria distillation.
 *
 * <p>Uses X-Internal-Secret for service-to-service auth.
 * Does NOT use RequestContextHolder — that fails in batch threads.</p>
 *
 * <p>The Archon /architecture endpoint returns an ArchitectureOutputDto
 * serialised with Jackson default camelCase naming. The Memoria
 * fact_extractor.py expects snake_case field names under an
 * "architecture_design" wrapper (components, style) and top-level
 * snake_case fields (adl_rules, fmea_risks, trade_offs, characteristics,
 * weaknesses, governance_score).
 *
 * This client normalises the camelCase DTO response to the snake_case
 * shape before returning it so the agent extractor always receives a
 * consistent payload regardless of how archon-api serialises its DTO.
 * </p>
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
     * Fetches and normalises the structured architecture output for an Archon conversation.
     *
     * @param sessionId the Archon conversation UUID
     * @return normalised snake_case payload map, or empty if unavailable
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
            Map<String, Object> normalised = normaliseArchonPayload(response);
            log.debug("ArchonMemoriaClient: normalised payload sessionId={} keys={}",
                    sessionId, normalised.keySet());
            return Optional.of(normalised);
        } catch (Exception ex) {
            log.warn("ArchonMemoriaClient.getConversationOutput failed sessionId={} error={}",
                    sessionId, ex.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Normalises an Archon ArchitectureOutputDto (camelCase Jackson serialisation)
     * into the snake_case shape expected by memoria-agent fact_extractor.py.
     *
     * <p>Mapping:
     * <pre>
     *   components + style + domain → architecture_design: { components, style, domain }
     *   adlRules                   → adl_rules
     *   adlDocument                → adl_document
     *   fmeaRisks                  → fmea_risks
     *   tradeOffs                  → trade_offs
     *   characteristics            → characteristics  (already matches)
     *   weaknesses                 → weaknesses        (already matches)
     * </pre>
     * All other fields are passed through as-is for LLM extraction.
     * </p>
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> normaliseArchonPayload(Map<String, Object> raw) {
        Map<String, Object> result = new LinkedHashMap<>();

        // Build architecture_design wrapper from flat DTO fields
        Map<String, Object> archDesign = new HashMap<>();
        putIfPresent(archDesign, raw, "style", "style");
        putIfPresent(archDesign, raw, "domain", "domain");
        putIfPresent(archDesign, raw, "systemType", "system_type");
        putIfPresent(archDesign, raw, "components", "components");
        putIfPresent(archDesign, raw, "interactions", "interactions");
        if (!archDesign.isEmpty()) {
            result.put("architecture_design", archDesign);
        }

        // Rename camelCase DTO fields to snake_case
        putIfPresent(result, raw, "adlRules", "adl_rules");
        putIfPresent(result, raw, "adlDocument", "adl_document");
        putIfPresent(result, raw, "fmeaRisks", "fmea_risks");
        putIfPresent(result, raw, "tradeOffs", "trade_offs");
        putIfPresent(result, raw, "characteristics", "characteristics");
        putIfPresent(result, raw, "weaknesses", "weaknesses");

        // Governance score — may be nested under structured_output or flat
        Object govScore = raw.get("governanceScore");
        if (govScore == null) {
            // Try nested structured_output if present
            Object structured = raw.get("structuredOutput");
            if (structured instanceof Map<?, ?> structuredMap) {
                govScore = structuredMap.get("governanceScore");
            }
        }
        if (govScore != null) {
            result.put("governance_score", govScore);
        }

        // Buy vs build analysis
        putIfPresent(result, raw, "buyVsBuildAnalysis", "buy_vs_build_analysis");

        // Pass remaining non-mapped fields through so LLM extraction can use them
        for (Map.Entry<String, Object> entry : raw.entrySet()) {
            String key = entry.getKey();
            if (!result.containsKey(key) && !isMappedCamelKey(key)) {
                result.put(key, entry.getValue());
            }
        }

        return result;
    }

    private void putIfPresent(
            Map<String, Object> target,
            Map<String, Object> source,
            String sourceKey,
            String targetKey) {
        Object value = source.get(sourceKey);
        if (value != null) {
            target.put(targetKey, value);
        }
    }

    private boolean isMappedCamelKey(String key) {
        return switch (key) {
            case "adlRules", "adlDocument", "fmeaRisks", "tradeOffs",
                 "components", "interactions", "style", "domain", "systemType",
                 "characteristics", "weaknesses", "governanceScore",
                 "buyVsBuildAnalysis", "structuredOutput" -> true;
            default -> false;
        };
    }

    private void applyInternalHeaders(HttpHeaders headers) {
        if (!internalSecret.isBlank()) {
            headers.set(INTERNAL_SECRET_HEADER, internalSecret);
        }
    }
}
