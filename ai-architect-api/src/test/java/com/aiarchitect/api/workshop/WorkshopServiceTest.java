package com.aiarchitect.api.workshop;

import com.aiarchitect.api.domain.model.Conversation;
import com.aiarchitect.api.workshop.client.WorkshopAgentClient;
import com.aiarchitect.api.workshop.domain.model.WorkshopAttribute;
import com.aiarchitect.api.workshop.domain.model.WorkshopMessage;
import com.aiarchitect.api.workshop.domain.model.WorkshopSession;
import com.aiarchitect.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopMessageRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopSessionRepository;
import com.aiarchitect.api.workshop.dto.ArchitectureImplicationDto;
import com.aiarchitect.api.workshop.dto.AttributeResolutionDto;
import com.aiarchitect.api.workshop.dto.AttributeSummaryDto;
import com.aiarchitect.api.workshop.dto.GenerationReadinessDto;
import com.aiarchitect.api.workshop.dto.QualityAttributeDto;
import com.aiarchitect.api.workshop.dto.UtilityTreeDto;
import com.aiarchitect.api.workshop.dto.WorkshopGenerationResponseDto;
import com.aiarchitect.api.workshop.dto.WorkshopMessageDto;
import com.aiarchitect.api.workshop.dto.WorkshopScenarioDto;
import com.aiarchitect.api.workshop.dto.WorkshopSessionDto;
import com.aiarchitect.api.workshop.dto.WorkshopTurnResponseDto;
import com.aiarchitect.api.workshop.exception.WorkshopTurnTimeoutException;
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
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
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

    // ── getUtilityTree ────────────────────────────────────────────────────────

    @Test
    void getUtilityTree_throws404WhenUtilityTreeNotPresent() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        assertThatThrownBy(() -> service.getUtilityTree(id, "u@ex.com"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    void getUtilityTree_returnsUtilityTreeDtoWhenPresent() {
        UUID id = UUID.randomUUID();
        // Minimal valid utility tree JSON matching toUtilityTreeDto field access
        String treeJson = "{\"generated_at_turn\":2,\"total_scenarios\":1,"
                + "\"architectural_drivers\":[\"Performance\"],"
                + "\"nodes\":[{\"node_id\":\"n1\",\"attribute_name\":\"Perf\","
                + "\"refinement\":\"High throughput\",\"scenario_id\":\"s1\","
                + "\"scenario_title\":\"Load test\",\"business_importance\":\"high\","
                + "\"technical_risk\":\"medium\",\"priority_label\":\"H/M\","
                + "\"rationale\":\"Core requirement\"}],"
                + "\"generation_rationale\":\"Driven by load requirements\"}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .utilityTree(treeJson)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        UtilityTreeDto dto = service.getUtilityTree(id, "u@ex.com");

        assertThat(dto.generatedAtTurn()).isEqualTo(2);
        assertThat(dto.nodes()).hasSize(1);
        assertThat(dto.architecturalDrivers()).containsExactly("Performance");
    }

    // ── getImplications ───────────────────────────────────────────────────────

    @Test
    void getImplications_returnsEmptyListWhenNone() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .architectureImplications(null)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<ArchitectureImplicationDto> result = service.getImplications(id, "u@ex.com");

        assertThat(result).isEmpty();
    }

    @Test
    void getImplications_returnsListWhenPresent() {
        UUID id = UUID.randomUUID();
        String implJson = "[{\"implication_id\":\"impl-1\",\"implication\":\"Use caching layer\","
                + "\"source_scenario_id\":\"s1\",\"source_scenario_title\":\"Load test\","
                + "\"tradeoff\":\"Memory vs speed\","
                + "\"affected_quality_attrs\":[\"Performance\"],"
                + "\"constraint_type\":\"must\","
                + "\"constraint_classification\":\"functional_constraint\","
                + "\"strength\":\"high\",\"measurable_condition\":\"<100ms\"}]";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .architectureImplications(implJson)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<ArchitectureImplicationDto> result = service.getImplications(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).implication()).isEqualTo("Use caching layer");
    }

    // ── getAttributes ─────────────────────────────────────────────────────────

    @Test
    void getAttributes_returnsAllAttributesWhenNoConfidenceFilter() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(id))
                .thenReturn(List.of());

        List<QualityAttributeDto> result = service.getAttributes(id, "u@ex.com", null);

        assertThat(result).isEmpty();
        verify(attributeRepo).findBySessionIdOrderByImportanceAscNameAsc(id);
        verify(attributeRepo, never())
                .findBySessionIdAndConfidenceOrderByImportanceAsc(any(), any());
    }

    @Test
    void getAttributes_delegatesToConfidenceFilteredQueryWhenConfidenceProvided() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(attributeRepo.findBySessionIdAndConfidenceOrderByImportanceAsc(id, "confirmed"))
                .thenReturn(List.of());

        List<QualityAttributeDto> result = service.getAttributes(id, "u@ex.com", "confirmed");

        assertThat(result).isEmpty();
        verify(attributeRepo).findBySessionIdAndConfidenceOrderByImportanceAsc(id, "confirmed");
        verify(attributeRepo, never()).findBySessionIdOrderByImportanceAscNameAsc(any());
    }

    // ── getResolutions ────────────────────────────────────────────────────────

    @Test
    void getResolutions_returnsEmptyListWhenContextJsonHasNoAttributes() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<AttributeResolutionDto> result = service.getResolutions(id, "u@ex.com");

        assertThat(result).isEmpty();
    }

    @Test
    void getResolutions_returnsDtosWhenAttributesPresentInContext() {
        UUID id = UUID.randomUUID();
        String ctx = "{\"attributes\":[{\"attribute_id\":\"a1\",\"name\":\"Performance\","
                + "\"questions_resolved_count\":1,"
                + "\"resolved_answers\":[{\"question\":\"latency?\",\"answer\":\"<100ms\","
                + "\"resolved_in_turn\":1,\"evidence_quote\":\"from spec\"}],"
                + "\"open_questions\":[\"How to scale?\"]}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<AttributeResolutionDto> result = service.getResolutions(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).attributeId()).isEqualTo("a1");
        assertThat(result.get(0).attributeName()).isEqualTo("Performance");
        assertThat(result.get(0).resolvedAnswers()).hasSize(1);
        assertThat(result.get(0).openQuestions()).containsExactly("How to scale?");
    }

    // ── getScenarios ──────────────────────────────────────────────────────────

    @Test
    void getScenarios_returnsEmptyListWhenNoScenariosInContext() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).isEmpty();
    }

    @Test
    void getScenarios_returnsCompleteCompletenessWhenAllFieldsPresentWithOperationalMetric() {
        UUID id = UUID.randomUUID();
        // All four fields are >= 10 chars and the measure contains "ms" (an operational metric).
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s1\","
                + "\"title\":\"Peak load scenario\","
                + "\"stimulus\":\"1000 concurrent users submit requests simultaneously\","
                + "\"source\":\"load tester\","
                + "\"environment\":\"production environment under peak demand\","
                + "\"artifact\":\"payment service\","
                + "\"response\":\"all requests are processed without error\","
                + "\"response_measure\":\"99 percent of requests complete within 500ms\","
                + "\"exercises_attributes\":[],"
                + "\"evidence_quote\":\"from design doc\","
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("complete");
    }

    @Test
    void getScenarios_returnsNeedsMeasureCompletenessWhenResponseMeasureAbsent() {
        UUID id = UUID.randomUUID();
        // stimulus + response present (>= 10 chars each), measure absent → "needs_measure"
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s2\","
                + "\"stimulus\":\"500 concurrent requests arrive at peak\","
                + "\"response\":\"system processes all requests correctly\","
                + "\"response_measure\":\"\","
                + "\"exercises_attributes\":[],"
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("needs_measure");
    }

    @Test
    void getScenarios_returnsNeedsOperationalMetricWhenMeasureLacksMetricUnit() {
        UUID id = UUID.randomUUID();
        // All three key fields >= 10 chars, but the measure has no operational metric keyword.
        // Avoid words in OPERATIONAL_METRIC_SIGNALS (ms, %, requests, transactions, etc.).
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s3\","
                + "\"stimulus\":\"User submits a payment via the checkout form\","
                + "\"response\":\"payment is confirmed and stored in the database\","
                + "\"response_measure\":\"the system behaves correctly under load always\","
                + "\"exercises_attributes\":[],"
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("needs_operational_metric");
    }

    @Test
    void getScenarios_returnsNeedsMeasureCompletenessWhenOnlyStimAndResponse() {
        UUID id = UUID.randomUUID();
        // stimulus + response present (both >= 10 chars), no measure → "needs_measure"
        // (partial requires populated < 2 to skip the needs_measure branch,
        //  so we test the correct branch: hr && hs && !hm → needs_measure)
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s4\","
                + "\"stimulus\":\"User clicks the submit button on the checkout form\","
                + "\"response\":\"form data is validated and stored in the database\","
                + "\"exercises_attributes\":[],"
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("needs_measure");
    }

    @Test
    void getScenarios_returnsPartialCompletenessWhenEnvironmentAloneIsPopulated() {
        UUID id = UUID.randomUUID();
        // environment + response populated (populated==2) but no stimulus → hr&&hs is false
        // → falls to populated >= 2 → "partial"
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s4b\","
                + "\"stimulus\":\"short\","
                + "\"environment\":\"production environment under heavy load\","
                + "\"response\":\"payment is confirmed and stored in the database\","
                + "\"exercises_attributes\":[],"
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("partial");
    }

    @Test
    void getScenarios_returnsAspirationalCompletenessWhenNoFieldsPopulated() {
        UUID id = UUID.randomUUID();
        // All fields blank → "aspirational"
        String ctx = "{\"scenarios\":[{"
                + "\"scenario_id\":\"s5\","
                + "\"stimulus\":\"\","
                + "\"response\":\"\","
                + "\"response_measure\":\"\","
                + "\"exercises_attributes\":[],"
                + "\"derived_in_turn\":1"
                + "}]}";
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson(ctx)
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        List<WorkshopScenarioDto> result = service.getScenarios(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).completeness()).isEqualTo("aspirational");
    }

    // ── getMessages ───────────────────────────────────────────────────────────

    @Test
    void getMessages_returnsEmptyListWhenNoMessagesExist() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(messageRepo.findBySessionIdOrderByTurnNumberAsc(id)).thenReturn(List.of());

        List<WorkshopMessageDto> result = service.getMessages(id, "u@ex.com");

        assertThat(result).isEmpty();
    }

    @Test
    void getMessages_returnsMappedMessageDtosInTurnOrder() {
        UUID id = UUID.randomUUID();
        UUID msgId = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        WorkshopMessage msg = WorkshopMessage.builder()
                .id(msgId)
                .session(session)
                .turnNumber(1)
                .userInput("What are the requirements?")
                .agentResponse("Could you clarify the expected load?")
                .workshopPhase("input_analysis")
                .createdAt(Instant.now())
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(messageRepo.findBySessionIdOrderByTurnNumberAsc(id)).thenReturn(List.of(msg));

        List<WorkshopMessageDto> result = service.getMessages(id, "u@ex.com");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).turnNumber()).isEqualTo(1);
        assertThat(result.get(0).userInput()).isEqualTo("What are the requirements?");
        assertThat(result.get(0).agentResponse()).isEqualTo("Could you clarify the expected load?");
    }

    // ── completeSession happy path ────────────────────────────────────────────

    @Test
    void completeSession_callsAgentAndPersistsIsCompleteFlag() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        ObjectNode summaryNode = objectMapper.createObjectNode();
        summaryNode.put("system_description", "Payment gateway");
        summaryNode.put("elicitation_completeness", "partial");
        summaryNode.put("completeness_rationale", "Core attributes captured");
        summaryNode.put("ready_for_architecture_pipeline", true);
        summaryNode.put("pipeline_readiness_notes", "Ready for pipeline");
        summaryNode.set("attributes", objectMapper.createArrayNode());
        summaryNode.set("open_questions", objectMapper.createArrayNode());
        when(workshopAgentClient.postWorkshopSummary(any())).thenReturn(summaryNode);

        AttributeSummaryDto dto = service.completeSession(id, "u@ex.com");

        assertThat(dto.systemDescription()).isEqualTo("Payment gateway");
        assertThat(dto.readyForArchitecturePipeline()).isTrue();

        ArgumentCaptor<WorkshopSession> cap = ArgumentCaptor.forClass(WorkshopSession.class);
        verify(sessionRepo).save(cap.capture());
        assertThat(cap.getValue().isComplete()).isTrue();
    }

    // ── sendToPipeline happy path ─────────────────────────────────────────────

    @Test
    void sendToPipeline_createsConversationAndPersistsPipelineIdWhenSessionIsComplete() {
        UUID sessionId = UUID.randomUUID();
        UUID convId = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(sessionId).userId("u@ex.com").systemName("Payments")
                .workshopPhase("complete").complete(true).contextJson("{}")
                // pipelineConversationId null → no duplicate suppression branch taken
                .build();
        when(sessionRepo.findByIdAndUserId(sessionId, "u@ex.com"))
                .thenReturn(Optional.of(session));
        when(attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId))
                .thenReturn(List.of());
        Conversation conversation = Conversation.builder()
                .id(convId).userId("u@ex.com").title("Payments").build();
        when(conversationService.resolveConversation(isNull(), eq("u@ex.com"), any()))
                .thenReturn(conversation);

        WorkshopService.SendToPipelineResult result =
                service.sendToPipeline(sessionId, "u@ex.com");

        assertThat(result.conversationId()).isEqualTo(convId);
        assertThat(result.initialMessage()).isNotBlank();

        ArgumentCaptor<WorkshopSession> cap = ArgumentCaptor.forClass(WorkshopSession.class);
        verify(sessionRepo).save(cap.capture());
        assertThat(cap.getValue().getPipelineConversationId()).isEqualTo(convId);
    }

    // ── processTurn timeout and error propagation ─────────────────────────────

    @Test
    void processTurn_throwsWorkshopTurnTimeoutExceptionWhenAgentRespondsWithGatewayTimeout() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        // Simulate WorkshopAgentClientImpl's timeout branch raising GATEWAY_TIMEOUT.
        ResponseStatusException gatewayTimeout = new ResponseStatusException(
                HttpStatus.GATEWAY_TIMEOUT, "Workshop agent timeout");
        when(workshopAgentClient.postWorkshopTurn(any())).thenThrow(gatewayTimeout);

        assertThatThrownBy(() -> service.processTurn(id, "u@ex.com", "hello"))
                .isInstanceOf(WorkshopTurnTimeoutException.class)
                .satisfies(e ->
                        assertThat(((WorkshopTurnTimeoutException) e).getSessionId())
                                .isEqualTo(id));
    }

    @Test
    void processTurn_rethrowsNonTimeoutResponseStatusExceptionFromAgent() {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        // BAD_GATEWAY (not GATEWAY_TIMEOUT) should be rethrown as-is.
        ResponseStatusException badGateway = new ResponseStatusException(
                HttpStatus.BAD_GATEWAY, "Workshop agent unavailable");
        when(workshopAgentClient.postWorkshopTurn(any())).thenThrow(badGateway);

        assertThatThrownBy(() -> service.processTurn(id, "u@ex.com", "hello"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.BAD_GATEWAY);
    }

    // ── listSessions ─────────────────────────────────────────────────────────

    @Test
    void listSessions_returnsEmptyListWhenUserHasNoSessions() {
        when(sessionRepo.findByUserIdOrderByCreatedAtDesc("u@ex.com")).thenReturn(List.of());

        List<WorkshopSessionDto> result = service.listSessions("u@ex.com");

        assertThat(result).isEmpty();
    }

    @Test
    void listSessions_returnsMappedDtosForAllUserSessions() {
        UUID id1 = UUID.randomUUID();
        UUID id2 = UUID.randomUUID();
        WorkshopSession s1 = WorkshopSession.builder()
                .id(id1).userId("u@ex.com").systemName("System A")
                .workshopPhase("intro").complete(false).contextJson("{}")
                .createdAt(Instant.now()).build();
        WorkshopSession s2 = WorkshopSession.builder()
                .id(id2).userId("u@ex.com").systemName("System B")
                .workshopPhase("elicit").complete(true).contextJson("{}")
                .createdAt(Instant.now()).build();
        when(sessionRepo.findByUserIdOrderByCreatedAtDesc("u@ex.com"))
                .thenReturn(List.of(s1, s2));

        List<WorkshopSessionDto> result = service.listSessions("u@ex.com");

        assertThat(result).hasSize(2);
        assertThat(result.get(0).systemName()).isEqualTo("System A");
        assertThat(result.get(1).systemName()).isEqualTo("System B");
        assertThat(result.get(1).isComplete()).isTrue();
    }

    // ── assessGenerationReadiness ─────────────────────────────────────────────

    @Test
    void assessGenerationReadiness_returnsReadinessDtoFromAgentResponse() throws Exception {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{\"key\":\"val\"}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));

        ObjectNode agentResponse = objectMapper.createObjectNode();
        agentResponse.put("overall_readiness", "HIGH");
        agentResponse.put("confidence_note", "Good coverage");
        agentResponse.put("can_produce_useful_output", true);
        agentResponse.putArray("attribute_preview");
        agentResponse.putArray("high_value_gaps");
        agentResponse.putArray("missing_domains");
        when(workshopAgentClient.postWorkshopAssessReadiness(any())).thenReturn(agentResponse);

        GenerationReadinessDto result = service.assessGenerationReadiness(id, "u@ex.com");

        assertThat(result.overallReadiness()).isEqualTo("HIGH");
        assertThat(result.confidenceNote()).isEqualTo("Good coverage");
        assertThat(result.canProduceUsefulOutput()).isTrue();
        assertThat(result.attributePreview()).isEmpty();
    }

    @Test
    void assessGenerationReadiness_throwsNotFoundWhenSessionDoesNotBelongToUser() {
        UUID id = UUID.randomUUID();
        when(sessionRepo.findByIdAndUserId(id, "other@ex.com")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.assessGenerationReadiness(id, "other@ex.com"))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(e -> ((ResponseStatusException) e).getStatusCode())
                .isEqualTo(HttpStatus.NOT_FOUND);
    }

    // ── generateAttributes ────────────────────────────────────────────────────

    @Test
    void generateAttributes_persistsUpdatedContextAndReturnsGenerationDto() throws Exception {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(sessionRepo.save(any())).thenReturn(session);

        ObjectNode generationResponse = objectMapper.createObjectNode();
        generationResponse.put("generation_count", 3);
        generationResponse.put("overall_readiness", "HIGH");
        generationResponse.put("confidence_note", "Strong signal");
        generationResponse.put("attributes_generated", 3);
        generationResponse.put("generation_summary", "Generated 3 attributes");
        generationResponse.put("can_continue_refining", true);
        generationResponse.put("continuation_prompt", "");
        generationResponse.putArray("attribute_preview");
        generationResponse.putArray("high_value_gaps");
        generationResponse.putArray("missing_domains");

        ObjectNode root = objectMapper.createObjectNode();
        root.put("updated_context_json", "{\"attributes\":[]}");
        root.set("generation_response", generationResponse);
        when(workshopAgentClient.postWorkshopGenerate(any())).thenReturn(root);

        when(attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(id))
                .thenReturn(List.of());

        WorkshopGenerationResponseDto result = service.generateAttributes(id, "u@ex.com");

        assertThat(result.sessionId()).isEqualTo(id);
        assertThat(result.generationCount()).isEqualTo(3);
        assertThat(result.overallReadiness()).isEqualTo("HIGH");
        verify(sessionRepo).save(any());
        verify(attributeRepo).deleteBySessionId(id);
    }

    @Test
    void generateAttributes_handlesUnparseableUpdatedContextGracefully() throws Exception {
        UUID id = UUID.randomUUID();
        WorkshopSession session = WorkshopSession.builder()
                .id(id).userId("u@ex.com").systemName("S")
                .workshopPhase("P").complete(false).contextJson("{}")
                .build();
        when(sessionRepo.findByIdAndUserId(id, "u@ex.com")).thenReturn(Optional.of(session));
        when(sessionRepo.save(any())).thenReturn(session);

        // updated_context_json is deliberately invalid JSON to trigger the warn branch
        ObjectNode generationResponse = objectMapper.createObjectNode();
        generationResponse.put("generation_count", 0);
        generationResponse.put("overall_readiness", "LOW");
        generationResponse.put("confidence_note", "");
        generationResponse.put("attributes_generated", 0);
        generationResponse.put("generation_summary", "");
        generationResponse.put("can_continue_refining", false);
        generationResponse.put("continuation_prompt", "");
        generationResponse.putArray("attribute_preview");
        generationResponse.putArray("high_value_gaps");
        generationResponse.putArray("missing_domains");

        ObjectNode root = objectMapper.createObjectNode();
        root.put("updated_context_json", "NOT VALID JSON {{{{");
        root.set("generation_response", generationResponse);
        when(workshopAgentClient.postWorkshopGenerate(any())).thenReturn(root);

        when(attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(id))
                .thenReturn(List.of());

        // Must not throw even when updated_context_json cannot be parsed
        assertThatCode(() -> service.generateAttributes(id, "u@ex.com"))
                .doesNotThrowAnyException();
    }
}

