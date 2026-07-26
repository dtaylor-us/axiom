package com.memoria.api.client;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

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
        RequestContextHolder.resetRequestAttributes();
        mockWebServer.shutdown();
    }

    @Test
    void archonFetchesArchitectureFromTheDirectServiceRoute() throws Exception {
        enqueueJson("{\"summary\":\"architecture output\"}");
        bindCallerHeaders();
        UUID sessionId = UUID.randomUUID();
        ArchonMemoriaClient client = new ArchonMemoriaClient(
                WebClient.builder(), mockWebServer.url("/").toString(), "internal-secret");

        Optional<Map<String, Object>> payload = client.getConversationOutput(sessionId);

        assertThat(payload).contains(Map.of("summary", "architecture output"));
        RecordedRequest request = mockWebServer.takeRequest();
        assertThat(request.getPath()).isEqualTo("/api/v1/sessions/" + sessionId + "/architecture");
        assertThat(request.getHeader("X-Axiom-Internal-Secret")).isEqualTo("internal-secret");
        assertThat(request.getHeader("Authorization")).isEqualTo("Bearer caller-token");
        assertThat(request.getHeader("X-Axiom-User-Id")).isEqualTo("caller-user");
    }

    @Test
    void specWeaverFetchesPackageFromTheDirectServiceRoute() throws Exception {
        enqueueJson("{\"briefText\":\"requirements package\"}");
        bindCallerHeaders();
        UUID sessionId = UUID.randomUUID();
        SpecWeaverMemoriaClient client = new SpecWeaverMemoriaClient(
                WebClient.builder(), mockWebServer.url("/").toString(), "internal-secret");

        Optional<Map<String, Object>> payload = client.getSessionPackage(sessionId);

        assertThat(payload).contains(Map.of("briefText", "requirements package"));
        RecordedRequest request = mockWebServer.takeRequest();
        assertThat(request.getPath()).isEqualTo("/api/v1/sessions/" + sessionId + "/package");
        assertThat(request.getHeader("X-Axiom-Internal-Secret")).isEqualTo("internal-secret");
        assertThat(request.getHeader("Authorization")).isEqualTo("Bearer caller-token");
        assertThat(request.getHeader("X-Axiom-User-Id")).isEqualTo("caller-user");
    }

    private void bindCallerHeaders() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("Authorization", "Bearer caller-token");
        request.addHeader("X-Axiom-User-Id", "caller-user");
        RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(request));
    }

    private void enqueueJson(String body) {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody(body));
    }
}
