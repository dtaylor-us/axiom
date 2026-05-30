package com.archon.api.config;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

import static org.assertj.core.api.Assertions.assertThatCode;

class OllamaHealthCheckTest {

    @Test
    void onApplicationEvent_completesWhenOllamaReturnsOk() {
        OllamaHealthCheck healthCheck = healthCheckWithResponse(
                Mono.just(ClientResponse.create(HttpStatus.OK).body("{}").build()));

        assertThatCode(() -> healthCheck.onApplicationEvent(null)).doesNotThrowAnyException();
    }

    @Test
    void onApplicationEvent_ignoresNonSuccessfulResponseWithoutThrowing() {
        OllamaHealthCheck healthCheck = healthCheckWithResponse(
                Mono.just(ClientResponse.create(HttpStatus.FOUND).build()));

        assertThatCode(() -> healthCheck.onApplicationEvent(null)).doesNotThrowAnyException();
    }

    @Test
    void onApplicationEvent_handlesEmptyResponseWithoutThrowing() {
        OllamaHealthCheck healthCheck = healthCheckWithResponse(Mono.empty());

        assertThatCode(() -> healthCheck.onApplicationEvent(null)).doesNotThrowAnyException();
    }

    @Test
    void onApplicationEvent_swallowsWebClientExceptions() {
        OllamaHealthCheck healthCheck = healthCheckWithResponse(Mono.error(
                WebClientResponseException.create(
                        HttpStatus.SERVICE_UNAVAILABLE.value(),
                        "Service Unavailable",
                        null,
                        null,
                        null)));

        assertThatCode(() -> healthCheck.onApplicationEvent(null)).doesNotThrowAnyException();
    }

    private static OllamaHealthCheck healthCheckWithResponse(Mono<ClientResponse> response) {
        OllamaHealthCheck healthCheck = new OllamaHealthCheck() {
            @Override
            WebClient.Builder webClientBuilder() {
                return WebClient.builder().exchangeFunction(_request -> response);
            }
        };
        ReflectionTestUtils.setField(healthCheck, "ollamaBaseUrl", "http://ollama.test");
        return healthCheck;
    }
}
