package com.memoria.api.service;

import com.memoria.api.config.MemoriaAgentConfig;
import com.memoria.api.dto.AgentDistillRequest;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

class MemoriaAgentClientTest {

    private MockWebServer mockWebServer;
    private MemoriaAgentConfig config;

    @BeforeEach
    void setUp() throws IOException {
        mockWebServer = new MockWebServer();
        mockWebServer.start();
        config = new MemoriaAgentConfig();
        config.setBaseUrl(mockWebServer.url("/").toString());
        config.setInternalSecret("test-secret");
        config.setTimeoutSeconds(1);
    }

    @AfterEach
    void tearDown() throws IOException {
        mockWebServer.shutdown();
    }

    @Test
    void distill_postsToAgentAndReturnsResponse() throws Exception {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""
                        {"session_id":"s1","candidates":[],"conflicts":[],"message":"ok"}
                        """));

        MemoriaAgentClient client = new MemoriaAgentClient(WebClient.builder(), config);

        assertThat(client.distill(request())).isNotNull();
        RecordedRequest recordedRequest = mockWebServer.takeRequest();
        assertThat(recordedRequest.getPath()).isEqualTo("/distill");
        assertThat(recordedRequest.getHeader("X-Internal-Secret")).isEqualTo("test-secret");
    }

    @Test
    void distill_returnsNullOnErrorResponse() {
        mockWebServer.enqueue(new MockResponse().setResponseCode(500).setBody("down"));
        MemoriaAgentClient client = new MemoriaAgentClient(WebClient.builder(), config);

        assertThat(client.distill(request())).isNull();
    }

    @Test
    void distill_returnsNullOnTimeout() {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBodyDelay(2, TimeUnit.SECONDS)
                .setBody("""
                        {"session_id":"s1","candidates":[],"conflicts":[],"message":"ok"}
                        """));
        MemoriaAgentClient client = new MemoriaAgentClient(WebClient.builder(), config);

        assertThat(client.distill(request())).isNull();
    }

    private AgentDistillRequest request() {
        return new AgentDistillRequest("s1", "p1", null, "summary", Map.of(), List.of());
    }
}
