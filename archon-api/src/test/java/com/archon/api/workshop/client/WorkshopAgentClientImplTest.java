package com.archon.api.workshop.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Unit tests for {@link WorkshopAgentClientImpl}.
 *
 * <p>Uses {@link MockWebServer} to simulate the Python agent HTTP layer without
 * requiring the agent process to be running.</p>
 */
class WorkshopAgentClientImplTest {

    private MockWebServer mockServer;
    private WorkshopAgentClientImpl client;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() throws IOException {
        mockServer = new MockWebServer();
        mockServer.start();

        client = new WorkshopAgentClientImpl(objectMapper);
        ReflectionTestUtils.setField(client, "agentBaseUrl", mockServer.url("/").toString());
        ReflectionTestUtils.setField(client, "internalSecret", "test-secret");
    }

    @AfterEach
    void tearDown() {
        try {
            mockServer.shutdown();
        } catch (IOException ignored) {
            // Server may already be stopped in network-failure tests.
        }
    }

    // ── postWorkshopTurn ─────────────────────────────────────────────────────

    @Test
    void postWorkshopTurn_returnsJsonNodeOnSuccessfulResponse() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"turn_response\":{\"agent_message\":\"hello\"},"
                        + "\"updated_context_json\":\"{}\"}"));

        JsonNode result = client.postWorkshopTurn(
                Map.of("session_id", "s1", "user_input", "hi", "context_json", "{}"));

        assertThat(result.path("turn_response").path("agent_message").asText())
                .isEqualTo("hello");
    }

    // ── postWorkshopSummary ──────────────────────────────────────────────────

    @Test
    void postWorkshopSummary_returnsJsonNodeOnSuccessfulResponse() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"system_description\":\"Payment service\"}"));

        JsonNode result = client.postWorkshopSummary(
                Map.of("session_id", "s1", "context_json", "{}"));

        assertThat(result.path("system_description").asText())
                .isEqualTo("Payment service");
    }

    // ── postWorkshopAssessReadiness ──────────────────────────────────────────

    @Test
    void postWorkshopAssessReadiness_returnsJsonNodeOnSuccessfulResponse() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"overall_readiness\":\"adequate\"}"));

        JsonNode result = client.postWorkshopAssessReadiness(
                Map.of("session_id", "s1", "context_json", "{}"));

        assertThat(result.path("overall_readiness").asText()).isEqualTo("adequate");
    }

    // ── postWorkshopGenerate ─────────────────────────────────────────────────

    @Test
    void postWorkshopGenerate_returnsJsonNodeOnSuccessfulResponse() {
        mockServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{\"generation_count\":2}"));

        JsonNode result = client.postWorkshopGenerate(
                Map.of("session_id", "s1", "context_json", "{}"));

        assertThat(result.path("generation_count").asInt()).isEqualTo(2);
    }

    // ── error handling ───────────────────────────────────────────────────────

    @Test
    void post_throwsBadGatewayWhenAgentReturnsServerError() {
        mockServer.enqueue(new MockResponse()
                .setResponseCode(500)
                .setBody("Internal Server Error"));

        assertThatThrownBy(() -> client.postWorkshopTurn(
                Map.of("session_id", "s1", "user_input", "hi", "context_json", "{}")))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.BAD_GATEWAY));
    }

    @Test
    void post_throwsBadGatewayWhenAgentReturnsClientError() {
        // 4xx responses also trigger the onStatus error handler → BAD_GATEWAY
        mockServer.enqueue(new MockResponse()
                .setResponseCode(422)
                .setBody("{\"detail\":\"Unprocessable entity\"}"));

        assertThatThrownBy(() -> client.postWorkshopTurn(
                Map.of("session_id", "s1", "user_input", "hi", "context_json", "{}")))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.BAD_GATEWAY));
    }

    @Test
    void post_throwsBadGatewayOnNetworkFailure() throws IOException {
        // Shut down the server before the request to simulate a connection-refused error.
        mockServer.shutdown();

        assertThatThrownBy(() -> client.postWorkshopTurn(
                Map.of("session_id", "s1", "user_input", "hi", "context_json", "{}")))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(e -> assertThat(((ResponseStatusException) e).getStatusCode())
                        .isEqualTo(HttpStatus.BAD_GATEWAY));
    }
}
