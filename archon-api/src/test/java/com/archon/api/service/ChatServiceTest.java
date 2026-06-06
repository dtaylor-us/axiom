package com.archon.api.service;

import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.model.MessageRole;
import com.archon.api.dto.AgentRequest;
import com.archon.api.dto.AgentResponse;
import com.archon.api.dto.ChatRequest;
import com.archon.api.exception.AgentCommunicationException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import reactor.core.publisher.Flux;
import reactor.test.StepVerifier;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith({MockitoExtension.class, OutputCaptureExtension.class})
class ChatServiceTest {

    @Mock private ConversationService conversationService;
    @Mock private AgentBridgeService agentBridgeService;
    @Mock private ArchitectureOutputService architectureOutputService;
    @Mock private GovernanceService governanceService;
    @Mock private TacticsService tacticsService;
    @Mock private BuyVsBuildService buyVsBuildService;
    @Mock private UsageService usageService;
    @Mock private PipelineRunService pipelineRunService;
    @Mock private PipelineRunBroadcaster pipelineRunBroadcaster;
    @Spy  private ObjectMapper objectMapper = new ObjectMapper();
    @InjectMocks private ChatService chatService;

    private ChatRequest createRequest(String message, UUID conversationId) {
        ChatRequest req = new ChatRequest();
        req.setMessage(message);
        req.setConversationId(conversationId);
        return req;
    }

    @Test
    void streamChat_savesUserMessageBeforeStreamingAgent() {
        UUID convId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any())).thenReturn(Flux.empty());

        StepVerifier.create(chatService.streamChat(
                createRequest("hello", convId), "user1"))
                // switchOnFirst emits a RUN_CREATED event before the (empty) agent stream
                .expectNextCount(1)
                .verifyComplete();

        verify(conversationService).saveMessage(
                conv, MessageRole.USER, "hello", null);
    }

    @Test
    void streamChat_savesAssistantMessageOnComplete() {
        UUID convId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());

        AgentResponse chunk = new AgentResponse();
        chunk.setType(AgentResponse.EventType.CHUNK);
        chunk.setContent("architecture ");
        AgentResponse chunk2 = new AgentResponse();
        chunk2.setType(AgentResponse.EventType.CHUNK);
        chunk2.setContent("overview");
        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.just(chunk, chunk2));

        StepVerifier.create(chatService.streamChat(
                createRequest("design a system", convId), "user1"))
                // RUN_CREATED + chunk1 + chunk2
                .expectNextCount(3)
                .verifyComplete();

        // Verify assistant message saved in doOnComplete.
        // Use timeout because saveMessage(ASSISTANT) is called inside
        // CompletableFuture.runAsync() — it fires after the stream completes,
        // on a separate thread. timeout() polls until the condition is met.
        verify(conversationService, timeout(2000).times(2)).saveMessage(
                any(), any(), any(), any());
        ArgumentCaptor<MessageRole> roleCaptor =
                ArgumentCaptor.forClass(MessageRole.class);
        ArgumentCaptor<String> contentCaptor =
                ArgumentCaptor.forClass(String.class);
        verify(conversationService, timeout(2000).times(2)).saveMessage(
                any(), roleCaptor.capture(), contentCaptor.capture(), any());
        assertEquals(MessageRole.ASSISTANT, roleCaptor.getAllValues().get(1));
        assertEquals("architecture overview", contentCaptor.getAllValues().get(1));
    }

    @Test
    void streamChat_createsNewConversationWhenIdIsNull() {
        Conversation newConv = Conversation.builder()
                .id(UUID.randomUUID()).userId("user1").title("hello").build();
        when(conversationService.resolveConversation(isNull(), eq("user1"), eq("hello")))
                .thenReturn(newConv);
        when(conversationService.getRecentMessages(any(), eq(20)))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any())).thenReturn(Flux.empty());

        StepVerifier.create(chatService.streamChat(
                createRequest("hello", null), "user1"))
                // switchOnFirst emits a RUN_CREATED event before the (empty) agent stream
                .expectNextCount(1)
                .verifyComplete();

        verify(conversationService).resolveConversation(isNull(), eq("user1"), eq("hello"));
    }

    @Test
    void streamChat_reusesExistingConversation() {
        UUID existing = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(existing).userId("user1").title("t").build();
        when(conversationService.resolveConversation(eq(existing), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(existing, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any())).thenReturn(Flux.empty());

        StepVerifier.create(chatService.streamChat(
                createRequest("continue", existing), "user1"))
                // switchOnFirst emits a RUN_CREATED event before the (empty) agent stream
                .expectNextCount(1)
                .verifyComplete();

        ArgumentCaptor<AgentRequest> captor =
                ArgumentCaptor.forClass(AgentRequest.class);
        verify(agentBridgeService).stream(captor.capture());
        assertEquals(existing.toString(), captor.getValue().getConversationId());
    }

    @Test
    void streamChat_persistsStructuredOutputAsValidJson() {
        UUID convId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());

        AgentResponse chunkEvt = new AgentResponse();
        chunkEvt.setType(AgentResponse.EventType.CHUNK);
        chunkEvt.setContent("report");

        AgentResponse completeEvt = new AgentResponse();
        completeEvt.setType(AgentResponse.EventType.COMPLETE);
        completeEvt.setPayload(Map.of("message", "Pipeline completed.", "stages", 11));

        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.just(chunkEvt, completeEvt));

        StepVerifier.create(chatService.streamChat(
                createRequest("design", convId), "user1"))
                // RUN_CREATED + chunkEvt + completeEvt
                .expectNextCount(3)
                .verifyComplete();

        // Verify ASSISTANT message was saved with valid JSON structured output.
        // The assistant save is triggered asynchronously after stream completion.
        ArgumentCaptor<MessageRole> roleCaptor =
                ArgumentCaptor.forClass(MessageRole.class);
        ArgumentCaptor<String> contentCaptor =
                ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> structuredCaptor =
                ArgumentCaptor.forClass(String.class);
        verify(conversationService, timeout(2000).times(2)).saveMessage(
                any(), roleCaptor.capture(), contentCaptor.capture(), structuredCaptor.capture());
        assertEquals(MessageRole.ASSISTANT, roleCaptor.getAllValues().get(1));
        assertEquals("report", contentCaptor.getAllValues().get(1));
        String json = structuredCaptor.getAllValues().get(1);
        assertNotNull(json);
        assertTrue(json.contains("\"message\""));
        assertTrue(json.contains("\"stages\""));
        // Ensure it's valid JSON (not Java Map.toString())
        assertFalse(json.contains("="), "Should be JSON, not Map.toString()");
    }

    @Test
    void streamChat_propagatesAgentError() {
        UUID convId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.error(
                        new AgentCommunicationException("agent down")));

        StepVerifier.create(chatService.streamChat(
                createRequest("hello", convId), "user1"))
                .expectError(AgentCommunicationException.class)
                .verify();

        // Error happened before the first agent signal, so no run was created.
        verify(pipelineRunService, never()).failRun(any(), any(), any());
    }

    @Test
    void streamChat_marksRunFailedWhenMidStreamErrorOccurs() {
        UUID convId = UUID.randomUUID();
        UUID runId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());
        when(pipelineRunService.createRun(conv, 0)).thenReturn(java.util.Optional.of(runId));

        AgentResponse stageStart = new AgentResponse();
        stageStart.setType(AgentResponse.EventType.STAGE_START);
        stageStart.setStage("requirement_challenge");

        when(agentBridgeService.stream(any())).thenReturn(
                Flux.concat(
                        Flux.just(stageStart),
                        Flux.error(new AgentCommunicationException("agent dropped"))
                )
        );

        StepVerifier.create(chatService.streamChat(
                createRequest("hello", convId), "user1"))
                // RUN_CREATED + STAGE_START then stream error
                .expectNextCount(2)
                .expectError(AgentCommunicationException.class)
                .verify();

        verify(pipelineRunService, atLeastOnce()).failRun(
                eq(runId),
                eq("requirement_challenge"),
                org.mockito.ArgumentMatchers.contains("Agent stream terminated before COMPLETE"));
    }

    @Test
    void streamChat_marksRunFailedWhenStreamCompletesWithoutCompleteEvent() {
        UUID convId = UUID.randomUUID();
        UUID runId = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(convId).userId("user1").title("t").build();
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conv);
        when(conversationService.getRecentMessages(convId, 20))
                .thenReturn(List.of());
        when(pipelineRunService.createRun(conv, 0)).thenReturn(java.util.Optional.of(runId));

        AgentResponse stageStart = new AgentResponse();
        stageStart.setType(AgentResponse.EventType.STAGE_START);
        stageStart.setStage("requirement_parsing");

        when(agentBridgeService.stream(any())).thenReturn(Flux.just(stageStart));

        StepVerifier.create(chatService.streamChat(
                createRequest("hello", convId), "user1"))
                // RUN_CREATED + STAGE_START
                .expectNextCount(2)
                .verifyComplete();

        verify(pipelineRunService, timeout(2000)).failRun(
                eq(runId),
                eq("requirement_parsing"),
                eq("Agent stream ended without COMPLETE event"));
    }

    @Test
    void auditEventWrite_logsSseAuditWithRequiredFields(CapturedOutput output) {
        UUID conversationId = UUID.randomUUID();
        when(pipelineRunBroadcaster.activeCount()).thenReturn(3);

        chatService.auditEventWrite(
                conversationId, "user1", "STAGE_START", "architecture_generation");

        assertTrue(output.getOut().contains("SSE_AUDIT write"));
        assertTrue(output.getOut().contains("conversationId=" + conversationId));
        assertTrue(output.getOut().contains("userId=user1"));
        assertTrue(output.getOut().contains("eventType=STAGE_START"));
        assertTrue(output.getOut().contains("stage=architecture_generation"));
        assertTrue(output.getOut().contains("emitterCount=3"));
        assertTrue(output.getOut().contains("threadId="));
    }

    @Test
    void streamChat_discardsEventWhenConversationIdDoesNotMatch() {
        UUID conversationId = UUID.randomUUID();
        Conversation conversation = Conversation.builder()
                .id(conversationId).userId("user1").title("t").build();
        AgentResponse wrongConversationEvent = new AgentResponse();
        wrongConversationEvent.setType(AgentResponse.EventType.STAGE_START);
        wrongConversationEvent.setStage("architecture_generation");
        wrongConversationEvent.setConversationId(UUID.randomUUID().toString());
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conversation);
        when(conversationService.getRecentMessages(conversationId, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.just(wrongConversationEvent));

        StepVerifier.create(chatService.streamChat(
                createRequest("design", conversationId), "user1"))
                .expectNextMatches(response ->
                        response.getType() == AgentResponse.EventType.RUN_CREATED)
                .verifyComplete();

        verify(pipelineRunService, never()).appendEvent(
                any(), eq(AgentResponse.EventType.STAGE_START.name()), any(), any());
    }

    @Test
    void streamChat_logsRoutingViolationWhenDiscarding(CapturedOutput output) {
        UUID conversationId = UUID.randomUUID();
        Conversation conversation = Conversation.builder()
                .id(conversationId).userId("user1").title("t").build();
        AgentResponse wrongConversationEvent = new AgentResponse();
        wrongConversationEvent.setType(AgentResponse.EventType.STAGE_COMPLETE);
        wrongConversationEvent.setStage("diagram_generation");
        wrongConversationEvent.setPayload(Map.of("conversationId", UUID.randomUUID().toString()));
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conversation);
        when(conversationService.getRecentMessages(conversationId, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.just(wrongConversationEvent));

        StepVerifier.create(chatService.streamChat(
                createRequest("design", conversationId), "user1"))
                .expectNextCount(1)
                .verifyComplete();

        assertTrue(output.getOut().contains("ROUTING_VIOLATION"));
        assertTrue(output.getOut().contains("expected=" + conversationId));
        assertTrue(output.getOut().contains("eventType=STAGE_COMPLETE"));
    }

    @Test
    void streamChat_forwardsEventWhenConversationIdMatches() {
        UUID conversationId = UUID.randomUUID();
        Conversation conversation = Conversation.builder()
                .id(conversationId).userId("user1").title("t").build();
        AgentResponse matchingConversationEvent = new AgentResponse();
        matchingConversationEvent.setType(AgentResponse.EventType.STAGE_START);
        matchingConversationEvent.setStage("architecture_generation");
        matchingConversationEvent.setConversationId(conversationId.toString());
        when(conversationService.resolveConversation(any(), eq("user1"), any()))
                .thenReturn(conversation);
        when(conversationService.getRecentMessages(conversationId, 20))
                .thenReturn(List.of());
        when(agentBridgeService.stream(any()))
                .thenReturn(Flux.just(matchingConversationEvent));

        StepVerifier.create(chatService.streamChat(
                createRequest("design", conversationId), "user1"))
                .expectNextMatches(response ->
                        response.getType() == AgentResponse.EventType.RUN_CREATED)
                .expectNextMatches(response ->
                        response.getType() == AgentResponse.EventType.STAGE_START
                                && "architecture_generation".equals(response.getStage()))
                .verifyComplete();
    }
}
