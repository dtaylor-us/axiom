package com.specweaver.api.agent;

import com.specweaver.api.config.AgentClientConfig;
import com.specweaver.api.exception.AgentCommunicationException;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SpecWeaverAgentClientTest {

    private MockWebServer mockWebServer;
    private SpecWeaverAgentClient client;

    @BeforeEach
    void setUp() throws Exception {
        mockWebServer = new MockWebServer();
        mockWebServer.start();
        AgentClientConfig config = new AgentClientConfig();
        config.setBaseUrl(mockWebServer.url("/").toString());
        config.setTimeoutSeconds(5);
        client = new SpecWeaverAgentClient(config);
    }

    @AfterEach
    void tearDown() throws Exception {
        mockWebServer.shutdown();
    }

    @Test
    void extract_returnsAgentExtractionResponse() {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""
                        {"sessionId":"s1","archInputPackageJson":"{}","success":true,"errorMessage":null}
                        """));

        AgentExtractionResponse response = client.extract(request());

        assertEquals("s1", response.sessionId());
        assertEquals("{}", response.archInputPackageJson());
    }

    @Test
    void extract_postsToAgentExtractEndpoint() throws Exception {
        mockWebServer.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""
                        {"sessionId":"s1","archInputPackageJson":"{}","success":true,"errorMessage":null}
                        """));

        client.extract(request());

        assertEquals("/agent/extract", mockWebServer.takeRequest().getPath());
    }

    @Test
    void extract_throwsAgentCommunicationExceptionOnErrorStatus() {
        mockWebServer.enqueue(new MockResponse().setResponseCode(500).setBody("down"));

        assertThrows(AgentCommunicationException.class, () -> client.extract(request()));
    }

    private AgentExtractionRequest request() {
        return new AgentExtractionRequest("s1", List.of(
                new AgentExtractionRequest.DocumentPayload("d1", "PLAIN_TEXT", "text", "doc.txt", "source")));
    }
}
