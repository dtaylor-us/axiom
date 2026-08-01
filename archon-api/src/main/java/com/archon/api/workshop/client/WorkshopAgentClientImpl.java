package com.archon.api.workshop.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.TimeoutException;

/**
 * WebClient implementation of {@link WorkshopAgentClient}.
 *
 * <p>Uses a fresh WebClient per request — workshop traffic is low volume.</p>
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class WorkshopAgentClientImpl implements WorkshopAgentClient {

    private final ObjectMapper objectMapper;

    /**
     * Workshop contexts can grow beyond the default 256KB WebClient buffer.
     * Raise the limit so /workshop/turn and /workshop/generate can round-trip
     * the full context_json safely.
     */
    private static final int MAX_IN_MEMORY_BYTES = 2 * 1024 * 1024; // 2MB

    /**
     * Timeout applied to all workshop agent calls.
     *
     * <p>Workshop turns make 8-10 sequential LLM calls (analyze_input, identify_gaps,
     * reconcile_gaps, resolve_questions, elicit_scenarios, infer_attributes, consolidation,
     * generate_utility_tree, synthesise_implications, generate_response). At scale, with
     * OpenAI 429 rate-limit retries adding up to 13 s each, a full turn can exceed 90 s.
     * Set to 180 s to accommodate the worst-case rate-limit backoff scenario.</p>
     */
    static final Duration WORKSHOP_CALL_TIMEOUT = Duration.ofSeconds(180);

    @Value("${agent.base-url}")
    private String agentBaseUrl;

    @Value("${agent.internal-secret}")
    private String internalSecret;

    @Override
    public JsonNode postWorkshopTurn(Map<String, Object> payload) {
        return post("/workshop/turn", payload);
    }

    @Override
    public JsonNode postWorkshopSummary(Map<String, Object> payload) {
        return post("/workshop/summary", payload);
    }

    @Override
    public JsonNode postWorkshopAssessReadiness(Map<String, Object> payload) {
        return post("/workshop/assess-readiness", payload);
    }

    @Override
    public JsonNode postWorkshopGenerate(Map<String, Object> payload) {
        return post("/workshop/generate", payload);
    }

    private JsonNode post(String path, Map<String, Object> payload) {
        try {
            ExchangeStrategies strategies = ExchangeStrategies.builder()
                    .codecs(cfg -> cfg.defaultCodecs().maxInMemorySize(MAX_IN_MEMORY_BYTES))
                    .build();

            String responseBody = WebClient.builder()
                    .baseUrl(agentBaseUrl)
                    .exchangeStrategies(strategies)
                    .defaultHeader(HttpHeaders.CONTENT_TYPE,
                            MediaType.APPLICATION_JSON_VALUE)
                    .defaultHeader("X-Internal-Secret", internalSecret)
                    .build()
                    .post()
                    .uri(path)
                    .bodyValue(payload)
                    .retrieve()
                    .onStatus(status -> status.isError(), resp ->
                            resp.bodyToMono(String.class).map(body ->
                                    new ResponseStatusException(
                                            HttpStatus.BAD_GATEWAY,
                                            "Workshop agent error: " + body)))
                    .bodyToMono(String.class)
                    .timeout(WORKSHOP_CALL_TIMEOUT)
                    .block();

            return objectMapper.readTree(responseBody);

        } catch (ResponseStatusException rse) {
            throw rse;
        } catch (Exception e) {
            if (e.getCause() instanceof TimeoutException) {
                log.warn("Workshop agent timed out at {} after {}s", path, WORKSHOP_CALL_TIMEOUT.toSeconds());
                throw new ResponseStatusException(HttpStatus.GATEWAY_TIMEOUT,
                        "Workshop agent timeout");
            }
            log.error("Failed to call workshop agent at {}: {}", path, e.getMessage());
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "Workshop agent unavailable");
        }
    }
}
