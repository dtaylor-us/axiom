package com.aiarchitect.api.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.ApplicationListener;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientException;

/**
 * Verifies that the local Ollama provider is reachable when the API starts.
 *
 * <p>The API still delegates all inference to the Python agent. This check is
 * only an early warning for local development so provider issues show up in
 * startup logs before the first pipeline request.</p>
 */
@Component
@Slf4j
@ConditionalOnProperty(name = "agent.llm-provider", havingValue = "ollama")
public class OllamaHealthCheck implements ApplicationListener<ApplicationReadyEvent> {

    @Value("${OLLAMA_BASE_URL:http://ollama:11434}")
    private String ollamaBaseUrl;

    /**
     * Calls Ollama's model tag endpoint and logs provider availability.
     *
     * @param event Spring Boot application-ready event
     */
    @Override
    public void onApplicationEvent(ApplicationReadyEvent event) {
        try {
            ResponseEntity<String> response = webClientBuilder()
                    .baseUrl(ollamaBaseUrl)
                    .build()
                    .get()
                    .uri("/api/tags")
                    .retrieve()
                    .toEntity(String.class)
                    .block();

            if (response != null && response.getStatusCode().is2xxSuccessful()) {
                log.info("OllamaHealthCheck: Ollama reachable at {}", ollamaBaseUrl);
            }
        } catch (WebClientException | IllegalStateException e) {
            log.warn(
                    "OllamaHealthCheck: Ollama not reachable at {}. "
                            + "Pipeline requests will fail until Ollama is available. Error: {}",
                    ollamaBaseUrl,
                    e.getMessage());
        }
    }

    WebClient.Builder webClientBuilder() {
        return WebClient.builder();
    }
}
