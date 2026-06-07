package com.archon.api.service;

import com.archon.api.client.AgentHttpClient;
import com.archon.api.dto.AgentRequest;
import com.archon.api.dto.AgentResponse;
import com.archon.api.exception.AgentCommunicationException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import reactor.core.publisher.Flux;
import reactor.test.StepVerifier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AgentBridgeServiceTest {

    @Mock private AgentHttpClient agentHttpClient;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private AgentBridgeService agentBridgeService;

    @BeforeEach
    void setUp() {
        agentBridgeService = new AgentBridgeService(agentHttpClient, objectMapper);
    }

    @Test
    void stream_returnsParsedAgentResponseForValidNdjsonLine() {
        String validJson = "{\"type\":\"CHUNK\",\"content\":\"hello\"}";
        when(agentHttpClient.stream(any())).thenReturn(Flux.just(validJson));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentBridgeService.stream(request))
                .assertNext(resp -> {
                    assertEquals(AgentResponse.EventType.CHUNK, resp.getType());
                    assertEquals("hello", resp.getContent());
                })
                .verifyComplete();
    }

    @Test
    void stream_returnsErrorTypeForMalformedJsonLine() {
        String malformed = "not-json{{{";
        when(agentHttpClient.stream(any())).thenReturn(Flux.just(malformed));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentBridgeService.stream(request))
                .assertNext(resp -> {
                    assertEquals(AgentResponse.EventType.ERROR, resp.getType());
                    assertNotNull(resp.getContent());
                })
                .verifyComplete();
    }

    @Test
    void stream_propagatesAgentCommunicationException() {
        when(agentHttpClient.stream(any())).thenReturn(
                Flux.error(new AgentCommunicationException("agent down")));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentBridgeService.stream(request))
                .expectErrorMatches(e ->
                        e instanceof AgentCommunicationException
                        && e.getMessage().equals("agent down"))
                .verify();
    }

    @Test
    void stream_wrapsNonAgentExceptionInAgentCommunicationException() {
        when(agentHttpClient.stream(any())).thenReturn(
                Flux.error(new RuntimeException("network failure")));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentBridgeService.stream(request))
                .expectErrorMatches(e ->
                        e instanceof AgentCommunicationException
                        && e.getMessage().contains("Agent stream failed"))
                .verify();
    }

    @Test
    void stream_parsesMultipleNdjsonLines() {
        String line1 = "{\"type\":\"STAGE_START\",\"stage\":\"parsing\"}";
        String line2 = "{\"type\":\"CHUNK\",\"content\":\"data\"}";
        String line3 = "{\"type\":\"COMPLETE\",\"conversationId\":\"c1\"}";
        when(agentHttpClient.stream(any()))
                .thenReturn(Flux.just(line1, line2, line3));

        AgentRequest request = AgentRequest.builder()
                .conversationId("c1").userMessage("hi").build();

        StepVerifier.create(agentBridgeService.stream(request))
                .assertNext(r -> assertEquals(AgentResponse.EventType.STAGE_START, r.getType()))
                .assertNext(r -> assertEquals(AgentResponse.EventType.CHUNK, r.getType()))
                .assertNext(r -> assertEquals(AgentResponse.EventType.COMPLETE, r.getType()))
                .verifyComplete();
    }
}
