package com.archon.api;

import com.archon.api.client.AgentHttpClient;
import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.model.Message;
import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.domain.repository.MessageRepository;
import com.archon.api.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Flux;

import java.io.IOException;
import java.net.URI;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
@org.testcontainers.junit.jupiter.Testcontainers(disabledWithoutDocker = true)
class ChatControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private JwtService jwtService;
    @Autowired private ConversationRepository conversationRepo;
    @Autowired private MessageRepository messageRepo;
    @MockBean private AgentHttpClient agentHttpClient;

    private String validToken;

    @BeforeEach
    void setUp() {
        messageRepo.deleteAll();
        conversationRepo.deleteAll();
        validToken = jwtService.generateToken("test@example.com");
    }

    @Test
    void streamChat_returns401WithoutToken() {
        webTestClient.post().uri("/api/v1/chat/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"message\":\"hello\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void streamChat_returns401WithInvalidToken() {
        webTestClient.post().uri("/api/v1/chat/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer invalid-token")
                .bodyValue("{\"message\":\"hello\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void streamChat_returnsEventStreamContentType() {
        String agentLine = "{\"type\":\"COMPLETE\",\"conversationId\":\"c1\",\"content\":\"done\"}";
        when(agentHttpClient.stream(any())).thenReturn(Flux.just(agentLine));

        webTestClient.post().uri("/api/v1/chat/stream")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"message\":\"design a payment system\"}")
                .exchange()
                .expectStatus().isOk()
                .expectHeader().contentTypeCompatibleWith(MediaType.TEXT_EVENT_STREAM);
    }

    @Test
    void streamChat_returns400ForInvalidRequestBody() {
        webTestClient.post().uri("/api/v1/chat/stream")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"message\":\"\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }

    @Test
    void streamChat_persistsConversationAndMessageToDb() throws Exception {
        String agentChunk = "{\"type\":\"CHUNK\",\"content\":\"hello back\"}";
        String agentComplete = "{\"type\":\"COMPLETE\",\"conversationId\":\"c1\"}";
        when(agentHttpClient.stream(any()))
                .thenReturn(Flux.just(agentChunk, agentComplete));

        webTestClient.post().uri("/api/v1/chat/stream")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"message\":\"build a microservice\"}")
                .exchange()
                .expectStatus().isOk();

        // Give a moment for doOnComplete to fire
        Thread.sleep(500);

        List<Conversation> conversations = conversationRepo.findAll();
        assertFalse(conversations.isEmpty(),
                "At least one conversation should be persisted");

        Conversation conv = conversations.get(0);
        assertEquals("test@example.com", conv.getUserId());

        List<Message> messages = messageRepo.findAll();
        assertTrue(messages.size() >= 1,
                "At least the user message should be persisted");
    }

    @Test
    void streamChat_returns503WhenAgentUnavailable() {
        WebClientRequestException agentDown = new WebClientRequestException(
                new IOException("agent down"),
                HttpMethod.POST,
                URI.create("http://agent:8001/agent/stream"),
                HttpHeaders.EMPTY);
        when(agentHttpClient.stream(any())).thenReturn(Flux.error(agentDown));

        webTestClient.post().uri("/api/v1/chat/stream")
                .header("Authorization", "Bearer " + validToken)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"message\":\"hello\"}")
                .exchange()
                .expectStatus().isEqualTo(503)
                .expectHeader().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON);
    }
}
