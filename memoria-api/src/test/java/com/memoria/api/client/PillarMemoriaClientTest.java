package com.memoria.api.client;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class PillarMemoriaClientTest {

    private MockWebServer mockWebServer;

    @BeforeEach
    void setUp() throws IOException {
        mockWebServer = new MockWebServer();
        mockWebServer.start();
    }

    @AfterEach
    void tearDown() throws IOException {
        mockWebServer.shutdown();
    }

    @Test
    void archonFetchesArchitectureFromTheDirectServiceRoute() throws Exception {
        enqueueJson("{\"summary\":\"architecture output\"}");
        UUID sessionId = UUID.randomUUID();
        ArchonMemoriaClient client = new ArchonMemoriaClient(
                WebClient.builder(), mockWebServer.url("/").toString(), "internal-secret");

        Optional<Map<String, Object>> payload = client.getConversationOutput(sessionId);

        assertThat(payload).contains(Map.of("summary", "architecture output"));
        RecordedRequest request = mockWebServer.takeRequest();
        assertThat(request.getPath()).isEqualTo("/api/v1/sessions/" + sessionId + "/architecture");
        assertThat(request.getHeader("X-Axiom-Internal-Secret")).isEqualTo("internal-secret");
    }

    @Test
    void specWeaverFetchesPackageFromTheDirectServiceRoute() throws Exception {
        enqueueJson("{\"briefText\":\"requirements package\"}");
        UUID sessionId = UUID.randomUUID();
        SpecWeaverMemoriaClient client = new SpecWeaverMemoriaClient(
                WebClient.builder(), mockWebServer.url("/").toString(), "internal-secret");

        Optional<Map<String, Object>> payload = client.getSessionPackage(sessionId);

        assertThat(payload).contains(Map.of("briefText", "requirements package"));
        RecordedRequest request = mockWebServer.takeRequest();
        assertThat(request.getPath()).isEqualTo("/api/v1/sessions/" + sessionId + "/package");
        assertThat(request.getHeader("X-Axiom-Internal-Secret")).isEqualTo("internal-secret");
    }

    private void enqueueJson(String body) {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody(body));
    }
}
