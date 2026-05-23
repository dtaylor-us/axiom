package com.aiarchitect.api.workshop;

import com.aiarchitect.api.workshop.client.WorkshopAgentClient;
import com.aiarchitect.api.workshop.domain.model.WorkshopSession;
import com.aiarchitect.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopMessageRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopSessionRepository;
import com.aiarchitect.api.workshop.dto.WorkshopSessionDto;
import com.aiarchitect.api.workshop.dto.WorkshopTurnResponseDto;
import com.aiarchitect.api.workshop.dto.GenerationReadinessDto;
import com.aiarchitect.api.workshop.dto.WorkshopGenerationResponseDto;
import com.aiarchitect.api.workshop.service.WorkshopService;
import com.aiarchitect.api.service.ConversationService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class WorkshopServiceTest {

    @Mock private WorkshopSessionRepository sessionRepo;
    @Mock private WorkshopAttributeRepository attributeRepo;
    @Mock private WorkshopMessageRepository messageRepo;
    @Mock private ConversationService conversationService;
    @Mock private WorkshopAgentClient workshopAgentClient;

    @InjectMocks
    private WorkshopService service;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(service, "objectMapper", objectMapper);
    }

    // ── createSession ────────────────────────────────────────────────────────

    @Test
    void createSession_savesSessionAndReturnsDto() {
        UUID id = UUID.randomUUID();
        WorkshopSession saved = WorkshopSession.builder()
                .id(id)
                .userId("user@example.com")
                .systemName("Payment Srv")
                .workshopPhase("CONTEXT_SETTING")
                .complete(false)
                .contextJson("{}")
                .build();

        when(sessionRepo.save(any())).thenReturn(saved);

        WorkshopSessionDto dto = service.createSession("user@example.com", "Payment Srv");

        assertThat(dto.systemName()).isEqualTo("Payment Srv");
        assertThat(dto.workshopPhase()).isEqualTo("CONTEXT_SETTING");
        verify(sessionRepo, times(2)).save(any());
    }

    // ── getSession ownership ─────────────────────────────────────────────────

    @Test
    void getSession_throwsNotFoundForWrongUser() {
        UUID id = UUID.randomUUID();
        when(sessionRepo.findByIdAndUserId(id, "other@example.com"))
                .thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.getSession(id, "other@example.com"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.NOT_FOUND);
    }

    // ── processTurn on completed session ─────────────────────────────────────

    @Test
    void processTurn_throwsConflictWhenSessionComplete() {
        UUID id = UUID.randomUUID();
        WorkshopSession completed = WorkshopSession.builder()
                .id(id)
                .userId("u@ex.com")
                .systemName("S")
                .workshopPhase("CONSOLIDATION")
                .complete(true)
                .contextJson("{}")
                .build();

        when(sessionRepo.findByIdAndUserId(id, "u@ex.com"))
                .thenReturn(Optional.of(completed));

        assertThatThrownBy(() -> service.processTurn(id, "u@ex.com", "hello"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.CONFLICT);
    }

    // ── completeSession idempotency guard ────────────────────────────────────

    @Test
    void completeSession_throwsConflictWhenAlreadyComplete() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id)
                .userId("u@ex.com")
                .systemName("S")
                .workshopPhase("CONSOLIDATION")
                .complete(true)
                .contextJson("{}")
                .build();

        when(sessionRepo.findByIdAndUserId(id, "u@ex.com"))
                .thenReturn(Optional.of(session));

        assertThatThrownBy(() -> service.completeSession(id, "u@ex.com"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.CONFLICT);
    }

    @Test
    void sendToPipeline_recentPipelineConversationReturnsExistingConversation() {
        UUID sessionId = UUID.randomUUID();
        UUID conversationId = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(sessionId)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("complete")
                .complete(true)
                .contextJson("{}")
                .pipelineConversationId(conversationId)
                .pipelineSentAt(Instant.now())
                .build();
        when(sessionRepo.findByIdAndUserId(sessionId, "u@ex.com"))
                .thenReturn(Optional.of(session));
        when(attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId))
                .thenReturn(java.util.List.of());

        var result = service.sendToPipeline(sessionId, "u@ex.com");

        assertThat(result.conversationId()).isEqualTo(conversationId);
        verify(conversationService, never()).resolveConversation(any(), any(), any());
    }

    // ── listSessions ─────────────────────────────────────────────────────────

    @Test
    void listSessions_returnsEmptyListWhenNone() {
        when(sessionRepo.findByUserIdOrderByCreatedAtDesc("u@ex.com"))
                .thenReturn(java.util.List.of());

        var result = service.listSessions("u@ex.com");
        assertThat(result).isEmpty();
    }

    // ── processTurn persistence ordering ───────────────────────────────────────

    @Test
    void processTurn_persistsUpdatedContextBeforeReturning() throws Exception {
        UUID sessionId = UUID.randomUUID();
        String initialCtx = "{\"session_id\":\"" + sessionId
                + "\",\"user_id\":\"u@ex.com\",\"workshop_phase\":\"input_analysis\"}";
        WorkshopSession session = WorkshopSession.builder()
                .id(sessionId)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("input_analysis")
                .complete(false)
                .contextJson(initialCtx)
                .turnCount(0)
                .build();

        when(sessionRepo.findByIdAndUserId(sessionId, "u@ex.com"))
                .thenReturn(Optional.of(session));

        String updatedCtx = "{\"session_id\":\"" + sessionId
                + "\",\"gaps\":[{\"gap_id\":\"g1\",\"filled\":true}]}";
        ObjectNode agentRoot = objectMapper.createObjectNode();
        agentRoot.put("updated_context_json", updatedCtx);
        ObjectNode turn = objectMapper.createObjectNode();
        turn.put("agent_message", "hello");
        turn.put("workshop_phase", "business_context");
        turn.put("turn_number", 1);
        agentRoot.set("turn_response", turn);

        when(workshopAgentClient.postWorkshopTurn(any())).thenReturn(agentRoot);

        WorkshopTurnResponseDto dto = service.processTurn(sessionId, "u@ex.com", "input");

        assertThat(dto.workshopPhase()).isEqualTo("business_context");

        ArgumentCaptor<WorkshopSession> saveCap = ArgumentCaptor.forClass(WorkshopSession.class);
        verify(sessionRepo).save(saveCap.capture());
        assertThat(saveCap.getValue().getContextJson()).isEqualTo(updatedCtx);

        InOrder inOrder = inOrder(workshopAgentClient, sessionRepo);
        inOrder.verify(workshopAgentClient).postWorkshopTurn(any());
        inOrder.verify(sessionRepo).save(any());
    }

    @Test
    void processTurn_with_gap_filled_in_agent_response_persists_context_json()
            throws Exception {
        UUID sessionId = UUID.randomUUID();
        String initialCtx = "{\"session_id\":\"" + sessionId
                + "\",\"user_id\":\"u@ex.com\",\"gaps\":["
                + "{\"gap_id\":\"g1\",\"filled\":false,\"description\":\"x\"}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(sessionId)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("input_analysis")
                .complete(false)
                .contextJson(initialCtx)
                .turnCount(0)
                .build();

        when(sessionRepo.findByIdAndUserId(sessionId, "u@ex.com"))
                .thenReturn(Optional.of(session));

        String updatedCtx = "{\"session_id\":\"" + sessionId
                + "\",\"gaps\":[{\"gap_id\":\"g1\",\"filled\":true,\"filled_in_turn\":1}]}";
        ObjectNode agentRoot = objectMapper.createObjectNode();
        agentRoot.put("updated_context_json", updatedCtx);
        ObjectNode turn = objectMapper.createObjectNode();
        turn.put("agent_message", "ok");
        turn.put("workshop_phase", "input_analysis");
        turn.put("turn_number", 1);
        agentRoot.set("turn_response", turn);

        when(workshopAgentClient.postWorkshopTurn(any())).thenReturn(agentRoot);

        service.processTurn(sessionId, "u@ex.com", "answers");

        ArgumentCaptor<WorkshopSession> cap = ArgumentCaptor.forClass(WorkshopSession.class);
        verify(sessionRepo).save(cap.capture());
        JsonNode persisted = objectMapper.readTree(cap.getValue().getContextJson());
        assertThat(persisted.path("gaps").get(0).path("filled").asBoolean()).isTrue();
    }

    @Test
    void processTurn_on_subsequent_turn_receives_context_with_previously_filled_gap()
            throws Exception {
        UUID sessionId = UUID.randomUUID();
        String afterFirstTurnCtx = "{\"session_id\":\"" + sessionId
                + "\",\"user_id\":\"u@ex.com\",\"gaps\":["
                + "{\"gap_id\":\"g1\",\"filled\":true,\"filled_in_turn\":1}]}";

        WorkshopSession sessionAfterFirst = WorkshopSession.builder()
                .id(sessionId)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("business_context")
                .complete(false)
                .contextJson(afterFirstTurnCtx)
                .turnCount(1)
                .build();

        when(sessionRepo.findByIdAndUserId(sessionId, "u@ex.com"))
                .thenReturn(Optional.of(sessionAfterFirst));

        ObjectNode secondResp = objectMapper.createObjectNode();
        secondResp.put("updated_context_json", afterFirstTurnCtx);
        ObjectNode turn = objectMapper.createObjectNode();
        turn.put("agent_message", "next");
        turn.put("workshop_phase", "business_context");
        turn.put("turn_number", 2);
        secondResp.set("turn_response", turn);

        when(workshopAgentClient.postWorkshopTurn(any())).thenReturn(secondResp);

        service.processTurn(sessionId, "u@ex.com", "more");

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> payloadCap =
                ArgumentCaptor.forClass(Map.class);
        verify(workshopAgentClient).postWorkshopTurn(payloadCap.capture());
        String sentCtx = (String) payloadCap.getValue().get("context_json");
        JsonNode node = objectMapper.readTree(sentCtx);
        assertThat(node.path("gaps").get(0).path("filled").asBoolean()).isTrue();
    }

    // ── assessGenerationReadiness / generateAttributes ─────────────────────────

    @Test
    void assessGenerationReadiness_doesNotCallRepositorySave() throws Exception {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("input_analysis")
                .complete(false)
                .contextJson("{\"session_id\":\"" + id
                        + "\",\"user_id\":\"u@ex.com\",\"generation_count\":0}")
                .build();

        when(sessionRepo.findByIdAndUserId(id, "u@ex.com"))
                .thenReturn(Optional.of(session));

        ObjectNode readiness = objectMapper.createObjectNode();
        readiness.put("overall_readiness", "adequate");
        readiness.put("confidence_note", "ok");
        readiness.set("attribute_preview", objectMapper.createArrayNode());
        readiness.set("high_value_gaps", objectMapper.createArrayNode());
        readiness.set("missing_domains", objectMapper.createArrayNode());
        readiness.put("can_produce_useful_output", true);
        when(workshopAgentClient.postWorkshopAssessReadiness(any())).thenReturn(readiness);

        GenerationReadinessDto dto = service.assessGenerationReadiness(id, "u@ex.com");

        assertThat(dto.overallReadiness()).isEqualTo("adequate");
        verify(sessionRepo, never()).save(any());
    }

    @Test
    void generateAttributes_persistsUpdatedContextJson() throws Exception {
        UUID id = UUID.randomUUID();
        String ctx = "{\"session_id\":\"" + id
                + "\",\"user_id\":\"u@ex.com\",\"turns\":[{\"turn_number\":1,\"user_input\":\"x\",\"agent_response\":\"y\"}],\"raw_inputs\":[\"x\"],\"generation_count\":0}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id)
                .userId("u@ex.com")
                .systemName("Sys")
                .workshopPhase("input_analysis")
                .complete(false)
                .contextJson(ctx)
                .build();

        when(sessionRepo.findByIdAndUserId(id, "u@ex.com"))
                .thenReturn(Optional.of(session));

        String updated = "{\"session_id\":\"" + id
                + "\",\"generation_count\":1,\"attributes\":[],\"attributes_stale\":false}";
        ObjectNode root = objectMapper.createObjectNode();
        root.put("updated_context_json", updated);
        ObjectNode genResp = objectMapper.createObjectNode();
        genResp.put("generation_count", 1);
        genResp.put("overall_readiness", "partial");
        genResp.put("confidence_note", "");
        genResp.put("attributes_generated", 0);
        genResp.set("attribute_preview", objectMapper.createArrayNode());
        genResp.set("high_value_gaps", objectMapper.createArrayNode());
        genResp.set("missing_domains", objectMapper.createArrayNode());
        genResp.put("generation_summary", "");
        genResp.put("can_continue_refining", true);
        genResp.put("continuation_prompt", "go on");
        root.set("generation_response", genResp);

        when(workshopAgentClient.postWorkshopGenerate(any())).thenReturn(root);

        WorkshopGenerationResponseDto dto = service.generateAttributes(id, "u@ex.com");

        assertThat(dto.generationCount()).isEqualTo(1);
        assertThat(dto.attributesStale()).isFalse();

        ArgumentCaptor<WorkshopSession> cap = ArgumentCaptor.forClass(WorkshopSession.class);
        verify(sessionRepo).save(cap.capture());
        assertThat(cap.getValue().getContextJson()).contains("\"generation_count\":1");

        verify(attributeRepo).deleteBySessionId(id);
    }
}
