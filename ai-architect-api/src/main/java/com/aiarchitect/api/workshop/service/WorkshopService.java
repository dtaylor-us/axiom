package com.aiarchitect.api.workshop.service;

import com.aiarchitect.api.domain.model.Conversation;
import com.aiarchitect.api.domain.model.MessageRole;
import com.aiarchitect.api.service.ConversationService;
import com.aiarchitect.api.workshop.domain.model.WorkshopAttribute;
import com.aiarchitect.api.workshop.domain.model.WorkshopMessage;
import com.aiarchitect.api.workshop.domain.model.WorkshopSession;
import com.aiarchitect.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopMessageRepository;
import com.aiarchitect.api.workshop.domain.repository.WorkshopSessionRepository;
import com.aiarchitect.api.workshop.dto.AttributePreviewDto;
import com.aiarchitect.api.workshop.dto.AttributeSummaryDto;
import com.aiarchitect.api.workshop.dto.GenerationReadinessDto;
import com.aiarchitect.api.workshop.dto.HighValueGapDto;
import com.aiarchitect.api.workshop.dto.AttributeResolutionDto;
import com.aiarchitect.api.workshop.dto.QualityAttributeDto;
import com.aiarchitect.api.workshop.dto.ResolvedAnswerDto;
import com.aiarchitect.api.workshop.dto.WorkshopGenerationResponseDto;
import com.aiarchitect.api.workshop.dto.WorkshopSessionDto;
import com.aiarchitect.api.workshop.client.WorkshopAgentClient;
import com.aiarchitect.api.workshop.dto.WorkshopScenarioDto;
import com.aiarchitect.api.workshop.dto.WorkshopTurnResponseDto;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Orchestrates Quality Attribute Workshop sessions.
 *
 * <p>This service owns all persistence. The Python workshop agent is
 * stateless — it receives the full WorkshopContext JSON each turn and
 * returns an updated context. Spring Boot persists the context_json in
 * workshop_sessions and denormalises confirmed attributes into workshop_attributes.
 *
 * <p>The sendToPipeline method converts the structured summary into natural
 * language prose (not raw JSON) before injecting it into a Conversation, so
 * the existing pipeline can process it transparently.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class WorkshopService {

    private final WorkshopSessionRepository sessionRepo;
    private final WorkshopAttributeRepository attributeRepo;
    private final WorkshopMessageRepository messageRepo;
    private final ConversationService conversationService;
    private final ObjectMapper objectMapper;
    private final WorkshopAgentClient workshopAgentClient;

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Creates a new workshop session for the given user and system name.
     */
    @Transactional
    public WorkshopSessionDto createSession(String userId, String systemName) {
        // Save first to obtain the DB-generated session UUID
        WorkshopSession session = WorkshopSession.builder()
                .userId(userId)
                .systemName(systemName)
                .workshopPhase("input_analysis")
                .contextJson("{}")
                .build();
        session = sessionRepo.save(session);

        // Backfill context_json with the fields required by WorkshopContext on the Python side
        // (session_id and user_id are non-optional Pydantic fields — "{}" would be rejected)
        String initialContext;
        try {
            initialContext = objectMapper.writeValueAsString(Map.of(
                    "session_id",    session.getId().toString(),
                    "user_id",       userId,
                    "system_name",   systemName,
                    "workshop_phase","input_analysis"
            ));
        } catch (Exception e) {
            log.warn("Could not serialise initial context, falling back to bare JSON");
            initialContext = String.format(
                    "{\"session_id\":\"%s\",\"user_id\":\"%s\",\"system_name\":\"%s\",\"workshop_phase\":\"input_analysis\"}",
                    session.getId(), userId, systemName);
        }
        session.setContextJson(initialContext);
        return toSessionDto(sessionRepo.save(session));
    }

    /**
     * Processes one conversational turn: calls the Python agent, persists
     * the updated context, upserts attributes, and appends the message record.
     */
    @Transactional
    public WorkshopTurnResponseDto processTurn(UUID sessionId,
                                               String userId,
                                               String userInput) {
        WorkshopSession session = requireSession(sessionId, userId);

        if (session.isComplete()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Workshop session is already complete");
        }

        // Build payload for the Python workshop agent.
        // Guard: if context_json is bare {} (e.g. from old data), reconstruct it
        // so Pydantic's required fields (session_id, user_id) are present.
        String contextJson = session.getContextJson();
        if (contextJson == null || contextJson.isBlank() || "{}".equals(contextJson.strip())
                || "\"{}\"".equals(contextJson.strip())) {
            try {
                contextJson = objectMapper.writeValueAsString(Map.of(
                        "session_id",    sessionId.toString(),
                        "user_id",       userId,
                        "system_name",   session.getSystemName(),
                        "workshop_phase","input_analysis"
                ));
                session.setContextJson(contextJson);
                sessionRepo.save(session);
                log.warn("Repaired empty context_json for session {}", sessionId);
            } catch (Exception e) {
                log.error("Could not repair context_json for session {}", sessionId, e);
            }
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("session_id", sessionId.toString());
        payload.put("user_input", userInput);
        payload.put("context_json", contextJson);

        // 1. Call Python agent with current context (stateless — full JSON round-trip).
        JsonNode agentResponse;
        try {
            agentResponse = workshopAgentClient.postWorkshopTurn(payload);
        } catch (org.springframework.web.server.ResponseStatusException rse) {
            if (org.springframework.http.HttpStatus.GATEWAY_TIMEOUT.equals(rse.getStatusCode())) {
                throw new com.aiarchitect.api.workshop.exception.WorkshopTurnTimeoutException(sessionId);
            }
            throw rse;
        }
        JsonNode turnResponse = agentResponse.path("turn_response");
        String updatedContextJson = agentResponse.path("updated_context_json").asText("{}");
        String agentMessage = turnResponse.path("agent_message").asText("");
        String phase = turnResponse.path("workshop_phase").asText(session.getWorkshopPhase());
        int turnNumber = turnResponse.path("turn_number").asInt(0);

        // Parse updated context for attribute upsert
        JsonNode updatedContext;
        try {
            updatedContext = objectMapper.readTree(updatedContextJson);
        } catch (Exception e) {
            log.warn("Could not parse updated_context_json; skipping attribute upsert");
            updatedContext = objectMapper.createObjectNode();
        }

        // 2. Persist updated context BEFORE building the response DTO so the next
        // HTTP turn loads gap fill state and conversation history from the database.
        session.setContextJson(updatedContextJson);
        session.setWorkshopPhase(phase);
        session.setTurnCount(session.getTurnCount() + 1);
        session.setLastUpdated(Instant.now());
        sessionRepo.save(session);

        // 3. Denormalised attributes for queryable access
        upsertAttributes(session, updatedContext);

        // Append message record
        WorkshopMessage msg = WorkshopMessage.builder()
                .session(session)
                .turnNumber(turnNumber)
                .userInput(userInput)
                .agentResponse(agentMessage)
                .workshopPhase(phase)
                .build();
        messageRepo.save(msg);

        // Build response from agent payload
        return buildTurnResponse(sessionId, turnResponse);
    }

    /**
     * Returns the session DTO for the given session.
     */
    @Transactional(readOnly = true)
    public WorkshopSessionDto getSession(UUID sessionId, String userId) {
        return toSessionDto(requireSession(sessionId, userId));
    }

    /**
     * Returns quality attributes for a session, optionally filtered by confidence tier.
     */
    @Transactional(readOnly = true)
    public List<QualityAttributeDto> getAttributes(UUID sessionId,
                                                    String userId,
                                                    String confidence) {
        requireSession(sessionId, userId);
        List<WorkshopAttribute> attrs = confidence != null
                ? attributeRepo.findBySessionIdAndConfidenceOrderByImportanceAsc(sessionId, confidence)
                : attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId);
        return attrs.stream().map(this::toAttributeDto).toList();
    }

    /**
     * Returns the resolution traceability for a workshop session:
     * which answers resolved which attribute questions, with evidence quotes.
     */
    @Transactional(readOnly = true)
    public List<AttributeResolutionDto> getResolutions(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);
        JsonNode ctx;
        try {
            ctx = objectMapper.readTree(session.getContextJson());
        } catch (Exception e) {
            return List.of();
        }
        JsonNode attrs = ctx.path("attributes");
        if (!attrs.isArray()) {
            return List.of();
        }
        List<AttributeResolutionDto> out = new ArrayList<>();
        for (JsonNode a : attrs) {
            List<ResolvedAnswerDto> resolved = parseResolvedAnswersNode(a.path("resolved_answers"));
            List<String> open = parseStringListFromJsonArray(a.path("open_questions"));
            String aid = a.path("attribute_id").asText("");
            String name = a.path("name").asText("");
            int resolvedCount = a.path("questions_resolved_count").asInt(resolved.size());
            out.add(new AttributeResolutionDto(
                    aid,
                    name,
                    resolved,
                    open,
                    resolvedCount,
                    open.size()));
        }
        return out;
    }

    /**
     * Returns workshop scenarios parsed from persisted {@code context_json}.
     *
     * <p>Completeness is recomputed from scenario fields — never taken from stored labels.</p>
     */
    @Transactional(readOnly = true)
    public List<WorkshopScenarioDto> getScenarios(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);
        JsonNode ctx;
        try {
            ctx = objectMapper.readTree(session.getContextJson());
        } catch (Exception e) {
            return List.of();
        }
        JsonNode arr = ctx.path("scenarios");
        if (!arr.isArray() || arr.isEmpty()) {
            return List.of();
        }
        List<WorkshopScenarioDto> out = new ArrayList<>();
        for (JsonNode n : arr) {
            String stimulus = n.path("stimulus").asText("");
            String environment = n.path("environment").asText("");
            String response = n.path("response").asText("");
            String measure = n.path("response_measure").asText("");
            String completeness = computeScenarioCompletenessFromFields(
                    stimulus, environment, response, measure);
            List<String> exercises = new ArrayList<>();
            JsonNode ex = n.path("exercises_attributes");
            if (ex.isArray()) {
                for (JsonNode x : ex) {
                    exercises.add(x.asText(""));
                }
            }
            out.add(new WorkshopScenarioDto(
                    n.path("scenario_id").asText(""),
                    n.path("title").asText(""),
                    stimulus,
                    n.path("source").asText(""),
                    environment,
                    n.path("artifact").asText(""),
                    response,
                    measure,
                    exercises,
                    n.path("evidence_quote").asText(""),
                    n.path("derived_in_turn").asInt(0),
                    completeness
            ));
        }
        return out;
    }

    /**
     * Mirrors Python {@code compute_scenario_completeness} for workshop scenarios.
     */
    static String computeScenarioCompletenessFromFields(
            String stimulus,
            String environment,
            String response,
            String responseMeasure) {
        String st = stimulus != null ? stimulus.strip() : "";
        String env = environment != null ? environment.strip() : "";
        String resp = response != null ? response.strip() : "";
        String meas = responseMeasure != null ? responseMeasure.strip() : "";
        boolean hs = st.length() >= 10;
        boolean he = env.length() >= 10;
        boolean hr = resp.length() >= 10;
        boolean hm = meas.length() >= 10;
        int populated = (hs ? 1 : 0) + (he ? 1 : 0) + (hr ? 1 : 0) + (hm ? 1 : 0);
        if (populated == 0) {
            return "aspirational";
        }
        if (hm && hr && hs) {
            return "complete";
        }
        if (hr && hs && !hm) {
            return "needs_measure";
        }
        if (populated >= 2) {
            return "partial";
        }
        return "aspirational";
    }

    /**
     * Marks the session complete and calls the Python agent for a structured
     * summary of all elicited quality attributes.
     */
    @Transactional
    public AttributeSummaryDto completeSession(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);

        if (session.isComplete()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "Session is already complete");
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("session_id", sessionId.toString());
        payload.put("context_json", session.getContextJson());

        JsonNode summaryNode = workshopAgentClient.postWorkshopSummary(payload);

        session.setComplete(true);
        sessionRepo.save(session);

        return toAttributeSummaryDto(summaryNode);
    }

    /**
     * Converts the workshop summary into natural language prose and injects it
     * as the first user message in a new Conversation, returning the conversation ID.
     *
     * <p>The formatted text is plain prose so the main pipeline agent treats it
     * as a normal architectural requirements message — not raw structured JSON.
     */
    @Transactional
    public UUID sendToPipeline(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);

        // Complete the session if not already done
        if (!session.isComplete()) {
            completeSession(sessionId, userId);
            // Re-fetch to get updated complete flag
            session = requireSession(sessionId, userId);
        }

        // Fetch confirmed attributes
        List<WorkshopAttribute> attrs =
                attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId);

        String requirementsText = formatWorkshopOutputAsRequirements(
                session.getSystemName(), attrs);

        // Create a new conversation seeded with this requirements text
        Conversation conversation = conversationService.resolveConversation(
                null, userId, requirementsText);

        conversationService.saveMessage(conversation, MessageRole.USER,
                requirementsText, null);

        log.info("Workshop session {} bridged to conversation {} for user {}",
                sessionId, conversation.getId(), userId);

        return conversation.getId();
    }

    /**
     * Lists all sessions for a user, most recent first.
     */
    @Transactional(readOnly = true)
    public List<WorkshopSessionDto> listSessions(String userId) {
        return sessionRepo.findByUserIdOrderByCreatedAtDesc(userId)
                .stream()
                .map(this::toSessionDto)
                .toList();
    }

    /**
     * Returns the conversation messages for a session in chronological order.
     */
    @Transactional(readOnly = true)
    public List<com.aiarchitect.api.workshop.dto.WorkshopMessageDto> getMessages(
            UUID sessionId, String userId) {
        requireSession(sessionId, userId);
        return messageRepo.findBySessionIdOrderByTurnNumberAsc(sessionId)
                .stream()
                .map(m -> new com.aiarchitect.api.workshop.dto.WorkshopMessageDto(
                        m.getId(),
                        m.getTurnNumber(),
                        m.getUserInput(),
                        m.getAgentResponse(),
                        m.getWorkshopPhase(),
                        m.getCreatedAt()))
                .toList();
    }

    /**
     * Read-only assessment for the generate UI — does not persist.
     */
    @Transactional(readOnly = true)
    public GenerationReadinessDto assessGenerationReadiness(
            UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);
        Map<String, Object> payload = new HashMap<>();
        payload.put("session_id", sessionId.toString());
        payload.put("context_json", session.getContextJson());
        JsonNode node = workshopAgentClient.postWorkshopAssessReadiness(payload);
        return mapGenerationReadiness(node);
    }

    /**
     * User-triggered attribute generation; persists updated context and all attributes.
     * Does not set {@code is_complete} on the session.
     */
    @Transactional
    public WorkshopGenerationResponseDto generateAttributes(
            UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);

        Map<String, Object> payload = new HashMap<>();
        payload.put("session_id", sessionId.toString());
        payload.put("context_json", session.getContextJson());

        JsonNode root = workshopAgentClient.postWorkshopGenerate(payload);
        String updatedContextJson = root.path("updated_context_json").asText("{}");
        JsonNode generationResponse = root.path("generation_response");

        session.setContextJson(updatedContextJson);
        session.setLastUpdated(Instant.now());
        sessionRepo.save(session);

        JsonNode updatedContext;
        try {
            updatedContext = objectMapper.readTree(updatedContextJson);
        } catch (Exception e) {
            log.warn("Could not parse updated_context_json after generate");
            updatedContext = objectMapper.createObjectNode();
        }

        replaceAllAttributesFromContext(session, updatedContext);

        return buildWorkshopGenerationResponseDto(
                sessionId, generationResponse, updatedContext);
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------

    private WorkshopSession requireSession(UUID sessionId, String userId) {
        return sessionRepo.findByIdAndUserId(sessionId, userId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Workshop session not found"));
    }

    /**
     * Upserts the denormalised workshop_attributes table from a fresh context snapshot.
     * Deletes existing rows for the session and re-inserts confirmed attributes.
     */
    private void upsertAttributes(WorkshopSession session, JsonNode context) {
        UUID sessionId = session.getId();
        attributeRepo.deleteBySessionId(sessionId);

        JsonNode attrs = context.path("attributes");
        if (!attrs.isArray()) return;

        for (JsonNode a : attrs) {
            if (!"confirmed".equals(a.path("confidence").asText())) continue;

            WorkshopAttribute entity = workshopAttributeFromContextNode(session, a);
            attributeRepo.save(entity);
        }
    }

    /**
     * Replaces denormalised rows with every attribute in context (all confidence levels).
     * Used after user-triggered generation so tentative/inferred attributes appear in GET.
     */
    private void replaceAllAttributesFromContext(WorkshopSession session, JsonNode context) {
        UUID sessionId = session.getId();
        attributeRepo.deleteBySessionId(sessionId);

        JsonNode attrs = context.path("attributes");
        if (!attrs.isArray()) {
            return;
        }
        for (JsonNode a : attrs) {
            WorkshopAttribute entity = workshopAttributeFromContextNode(session, a);
            attributeRepo.save(entity);
        }
    }

    private WorkshopAttribute workshopAttributeFromContextNode(
            WorkshopSession session, JsonNode a) {
        JsonNode scenarios = a.path("scenarios");
        String scenarioStr;
        if (scenarios.isArray() && !scenarios.isEmpty()) {
            try {
                scenarioStr = objectMapper.writeValueAsString(scenarios.get(0));
            } catch (Exception e) {
                scenarioStr = scenarios.get(0).toString();
            }
        } else {
            JsonNode legacy = a.path("scenario");
            scenarioStr = legacy.isMissingNode() || legacy.isNull()
                    ? "{}"
                    : legacy.toString();
        }

        Integer firstGp = a.hasNonNull("first_generation_pass")
                ? a.path("first_generation_pass").asInt()
                : null;
        Integer lastGp = a.hasNonNull("last_generation_pass")
                ? a.path("last_generation_pass").asInt()
                : null;
        String desc = a.hasNonNull("description")
                ? a.path("description").asText()
                : null;

        JsonNode raNode = a.path("resolved_answers");
        String resolvedJson = raNode.isArray() ? raNode.toString() : "[]";
        int qResolved = a.path("questions_resolved_count").asInt(0);
        String lastSummary = a.hasNonNull("last_update_summary")
                ? a.path("last_update_summary").asText(null)
                : null;
        Integer lastTurn = a.hasNonNull("last_updated_turn")
                ? a.path("last_updated_turn").asInt()
                : null;

        return WorkshopAttribute.builder()
                .session(session)
                .attributeId(a.path("attribute_id").asText(UUID.randomUUID().toString()))
                .name(a.path("name").asText(""))
                .category(a.path("category").asText(""))
                .confidence(a.path("confidence").asText("tentative"))
                .importance(a.path("importance").asText("medium"))
                .description(desc)
                .scenarioJson(scenarioStr)
                .evidenceQuotes(a.path("evidence_quotes").toString())
                .openQuestions(a.path("open_questions").toString())
                .derivedInTurn(a.path("derived_in_turn").isNull()
                        ? null
                        : a.path("derived_in_turn").asInt())
                .firstGenerationPass(firstGp)
                .lastGenerationPass(lastGp)
                .resolvedAnswers(resolvedJson)
                .questionsResolvedCount(qResolved)
                .lastUpdateSummary(lastSummary)
                .lastUpdatedTurn(lastTurn)
                .build();
    }

    private GenerationReadinessDto mapGenerationReadiness(JsonNode node) {
        List<AttributePreviewDto> previews = new ArrayList<>();
        JsonNode ap = node.path("attribute_preview");
        if (ap.isArray()) {
            for (JsonNode p : ap) {
                previews.add(new AttributePreviewDto(
                        p.path("name").asText(""),
                        p.path("confidence").asText(""),
                        p.path("reason").asText("")));
            }
        }
        List<HighValueGapDto> gaps = new ArrayList<>();
        JsonNode hg = node.path("high_value_gaps");
        if (hg.isArray()) {
            for (JsonNode g : hg) {
                gaps.add(new HighValueGapDto(
                        g.path("gap_id").asText(""),
                        g.path("description").asText(""),
                        g.path("impact").asText("")));
            }
        }
        List<String> missing = new ArrayList<>();
        JsonNode md = node.path("missing_domains");
        if (md.isArray()) {
            for (JsonNode m : md) {
                missing.add(m.asText(""));
            }
        }
        return new GenerationReadinessDto(
                node.path("overall_readiness").asText(""),
                node.path("confidence_note").asText(""),
                previews,
                gaps,
                missing,
                node.path("can_produce_useful_output").asBoolean(false));
    }

    private WorkshopGenerationResponseDto buildWorkshopGenerationResponseDto(
            UUID sessionId,
            JsonNode generationResponse,
            JsonNode updatedContext) {
        List<QualityAttributeDto> attrs =
                attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId)
                        .stream()
                        .map(this::toAttributeDto)
                        .toList();

        List<AttributePreviewDto> previews = new ArrayList<>();
        JsonNode ap = generationResponse.path("attribute_preview");
        if (ap.isArray()) {
            for (JsonNode p : ap) {
                previews.add(new AttributePreviewDto(
                        p.path("name").asText(""),
                        p.path("confidence").asText(""),
                        p.path("reason").asText("")));
            }
        }
        List<HighValueGapDto> gaps = new ArrayList<>();
        JsonNode hg = generationResponse.path("high_value_gaps");
        if (hg.isArray()) {
            for (JsonNode g : hg) {
                gaps.add(new HighValueGapDto(
                        g.path("gap_id").asText(""),
                        g.path("description").asText(""),
                        g.path("impact").asText("")));
            }
        }
        List<String> missing = new ArrayList<>();
        JsonNode md = generationResponse.path("missing_domains");
        if (md.isArray()) {
            for (JsonNode m : md) {
                missing.add(m.asText(""));
            }
        }

        return new WorkshopGenerationResponseDto(
                sessionId,
                generationResponse.path("generation_count").asInt(0),
                generationResponse.path("overall_readiness").asText(""),
                generationResponse.path("confidence_note").asText(""),
                generationResponse.path("attributes_generated").asInt(attrs.size()),
                previews,
                gaps,
                missing,
                generationResponse.path("generation_summary").asText(""),
                attrs,
                generationResponse.path("can_continue_refining").asBoolean(true),
                generationResponse.path("continuation_prompt").asText(""),
                updatedContext.path("attributes_stale").asBoolean(false));
    }

    private WorkshopTurnResponseDto buildTurnResponse(UUID sessionId, JsonNode node) {
        // node is already the turn_response sub-object from the Python agent
        JsonNode gapSummaryNode = node.path("gap_summary");
        JsonNode gaps = gapSummaryNode.path("open_gaps");
        List<WorkshopTurnResponseDto.OpenGapDto> openGaps = List.of();
        if (gaps.isArray()) {
            openGaps = new java.util.ArrayList<>();
            for (JsonNode g : gaps) {
                openGaps.add(new WorkshopTurnResponseDto.OpenGapDto(
                        g.path("gap_id").asText(""),
                        g.path("category").asText(""),
                        g.path("description").asText(""),
                        g.path("priority").asText("medium"),
                        g.path("residual_question").asText(""),
                        g.path("resolution_confidence").asDouble(0.0)
                ));
            }
        }
        WorkshopTurnResponseDto.GapSummaryDto gapSummary =
                new WorkshopTurnResponseDto.GapSummaryDto(
                        gapSummaryNode.path("total").asInt(0),
                        gapSummaryNode.path("filled").asInt(0),
                        gapSummaryNode.path("completion_pct").asInt(0),
                        gapSummaryNode.path("in_progress_count").asInt(0),
                        openGaps
                );

        List<String> questionsAsked = new java.util.ArrayList<>();
        JsonNode questions = node.path("questions_asked");
        if (questions.isArray()) {
            for (JsonNode q : questions) questionsAsked.add(q.asText());
        }

        // non_qa_concerns from context (populated by ConsolidationEngine)
        List<WorkshopTurnResponseDto.NonQaConcernDto> nonQaConcerns = List.of();
        JsonNode concernsNode = node.path("non_qa_concerns");
        if (concernsNode.isArray()) {
            nonQaConcerns = new java.util.ArrayList<>();
            for (JsonNode c : concernsNode) {
                nonQaConcerns.add(new WorkshopTurnResponseDto.NonQaConcernDto(
                        c.path("name").asText(""),
                        c.path("description").asText(""),
                        c.path("category").asText("other")
                ));
            }
        }

        return new WorkshopTurnResponseDto(
                sessionId,
                node.path("turn_number").asInt(0),
                node.path("workshop_phase").asText(""),
                node.path("agent_message").asText(""),
                questionsAsked,
                gapSummary,
                List.of(),
                node.path("is_complete").asBoolean(false),
                node.path("has_sufficient_attributes").asBoolean(false),
                nonQaConcerns
        );
    }

    private WorkshopSessionDto toSessionDto(WorkshopSession s) {
        JsonNode ctx;
        try {
            ctx = objectMapper.readTree(s.getContextJson());
        } catch (Exception e) {
            ctx = objectMapper.createObjectNode();
        }

        // total_gaps / filled_gaps are @property computed values in Python and are
        // NOT serialised into context_json — iterate the gaps array directly.
        JsonNode gapsArray = ctx.path("gaps");
        int totalGaps = gapsArray.isArray() ? gapsArray.size() : 0;
        int filledGaps = 0;
        int inProgressGaps = 0;
        if (gapsArray.isArray()) {
            for (JsonNode g : gapsArray) {
                if (g.path("filled").asBoolean(false)) {
                    filledGaps++;
                } else if (g.path("resolution_confidence").asDouble(0.0) >= 0.5) {
                    inProgressGaps++;
                }
            }
        }
        int gapPct = totalGaps > 0 ? (int) Math.round((double) filledGaps / totalGaps * 100.0) : 0;

        // has_sufficient_attributes is also a @property — replicate its logic:
        // ≥3 confirmed attributes each with at least one non-aspirational scenario.
        JsonNode attrsArray  = ctx.path("attributes");
        JsonNode confirmedIdNode = ctx.path("confirmed_attributes");
        java.util.Set<String> confirmedIds = new java.util.HashSet<>();
        if (confirmedIdNode.isArray()) {
            for (JsonNode id : confirmedIdNode) confirmedIds.add(id.asText());
        }
        int groundedConfirmed = 0;
        if (attrsArray.isArray()) {
            for (JsonNode a : attrsArray) {
                String id = a.path("attribute_id").asText("");
                if (!confirmedIds.contains(id)) continue;
                JsonNode scenarios = a.path("scenarios");
                if (!scenarios.isArray() || scenarios.isEmpty()) continue;
                String completeness = scenarios.get(0).path("completeness").asText("aspirational");
                if (!"aspirational".equals(completeness)) groundedConfirmed++;
            }
        }
        boolean hasSuf = groundedConfirmed >= 3;

        List<WorkshopAttribute> allAttrs =
                attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(s.getId());
        int attributeCount = allAttrs.size();
        int confirmedCount = (int) allAttrs.stream()
                .filter(a -> "confirmed".equals(a.getConfidence())).count();

        int generationCount = ctx.path("generation_count").asInt(0);
        boolean attributesStale = ctx.path("attributes_stale").asBoolean(false);

        // Build open-gap list for the Information Gaps panel
        List<WorkshopTurnResponseDto.OpenGapDto> openGaps = new java.util.ArrayList<>();
        if (gapsArray.isArray()) {
            for (JsonNode g : gapsArray) {
                if (!g.path("filled").asBoolean(false)) {
                    openGaps.add(new WorkshopTurnResponseDto.OpenGapDto(
                            g.path("gap_id").asText(""),
                            g.path("category").asText(""),
                            g.path("description").asText(""),
                            g.path("priority").asText("medium"),
                            g.path("residual_question").asText(""),
                            g.path("resolution_confidence").asDouble(0.0)
                    ));
                }
            }
        }

        return new WorkshopSessionDto(
                s.getId(),
                s.getSystemName(),
                s.getWorkshopPhase(),
                s.getTurnCount(),
                totalGaps,
                filledGaps,
                inProgressGaps,
                gapPct,
                attributeCount,
                confirmedCount,
                s.isComplete(),
                hasSuf,
                hasSuf && s.isComplete(),
                openGaps,
                s.getCreatedAt(),
                s.getLastUpdated(),
                generationCount,
                attributesStale
        );
    }

    private QualityAttributeDto toAttributeDto(WorkshopAttribute a) {
        return new QualityAttributeDto(
                a.getAttributeId(),
                a.getName(),
                a.getCategory(),
                a.getImportance(),
                a.getConfidence(),
                a.getDescription(),
                computeScenarioCompleteness(a.getScenarioJson()),
                parseStringList(a.getOpenQuestions()),
                parseStringList(a.getEvidenceQuotes()),
                a.getFirstGenerationPass(),
                a.getLastGenerationPass(),
                parseResolvedAnswersJson(a.getResolvedAnswers()),
                a.getQuestionsResolvedCount(),
                a.getLastUpdateSummary(),
                a.getLastUpdatedTurn()
        );
    }

    private List<ResolvedAnswerDto> parseResolvedAnswersJson(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            JsonNode arr = objectMapper.readTree(json);
            return parseResolvedAnswersNode(arr);
        } catch (Exception e) {
            return List.of();
        }
    }

    private List<ResolvedAnswerDto> parseResolvedAnswersNode(JsonNode arr) {
        if (arr == null || !arr.isArray()) {
            return List.of();
        }
        List<ResolvedAnswerDto> result = new ArrayList<>();
        for (JsonNode x : arr) {
            result.add(new ResolvedAnswerDto(
                    x.path("question").asText(""),
                    x.path("answer").asText(""),
                    x.path("resolved_in_turn").asInt(0),
                    x.path("evidence_quote").asText("")));
        }
        return result;
    }

    private List<String> parseStringListFromJsonArray(JsonNode node) {
        if (node == null || !node.isArray()) {
            return List.of();
        }
        List<String> result = new ArrayList<>();
        for (JsonNode n : node) {
            result.add(n.asText(""));
        }
        return result;
    }

    private String computeScenarioCompleteness(String scenarioJson) {
        if (scenarioJson == null || scenarioJson.isBlank()) return "aspirational";
        try {
            JsonNode scenario = objectMapper.readTree(scenarioJson);
            String[] required = {"stimulus", "source", "environment", "response", "response_measure"};
            long present = 0;
            for (String f : required) {
                if (!scenario.path(f).asText("").isBlank()) present++;
            }
            if (present == required.length) return "complete";
            if (scenario.path("response_measure").asText("").isBlank()) return "needs_measure";
            if (present >= 3) return "partial";
            return "aspirational";
        } catch (Exception e) {
            return "aspirational";
        }
    }

    private List<String> parseStringList(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            JsonNode node = objectMapper.readTree(json);
            if (node.isArray()) {
                List<String> result = new java.util.ArrayList<>();
                for (JsonNode n : node) result.add(n.asText());
                return result;
            }
        } catch (Exception ignored) {}
        return List.of();
    }

    private AttributeSummaryDto toAttributeSummaryDto(JsonNode node) {
        List<AttributeSummaryDto.SummaryAttributeDto> attrs = new java.util.ArrayList<>();
        JsonNode attrArray = node.path("attributes");
        if (attrArray.isArray()) {
            for (JsonNode a : attrArray) {
                JsonNode sc = a.path("scenario");
                AttributeSummaryDto.ScenarioDto scenario = new AttributeSummaryDto.ScenarioDto(
                        sc.path("stimulus").asText(""),
                        sc.path("source").asText(""),
                        sc.path("environment").asText(""),
                        sc.path("artifact").asText(""),
                        sc.path("response").asText(""),
                        sc.path("response_measure").asText(""),
                        sc.path("completeness").asText("")
                );
                attrs.add(new AttributeSummaryDto.SummaryAttributeDto(
                        a.path("name").asText(""),
                        a.path("importance").asText(""),
                        a.path("confidence").asText(""),
                        a.path("category").asText(""),
                        a.path("description").asText(""),
                        scenario,
                        a.path("evidence").asText("")
                ));
            }
        }
        List<String> openQuestions = new java.util.ArrayList<>();
        JsonNode oqNode = node.path("open_questions");
        if (oqNode.isArray()) {
            for (JsonNode q : oqNode) openQuestions.add(q.asText());
        }
        return new AttributeSummaryDto(
                node.path("system_description").asText(""),
                attrs,
                openQuestions,
                node.path("elicitation_completeness").asText(""),
                node.path("completeness_rationale").asText(""),
                node.path("ready_for_architecture_pipeline").asBoolean(false),
                node.path("pipeline_readiness_notes").asText("")
        );
    }

    /**
     * Formats workshop output as natural language prose suitable for the
     * main pipeline agent. Does NOT inject structured JSON.
     */
    private String formatWorkshopOutputAsRequirements(String systemName,
                                                       List<WorkshopAttribute> attributes) {
        StringBuilder sb = new StringBuilder();
        sb.append("I have completed a Quality Attribute Workshop for ")
          .append(systemName)
          .append(". Based on the workshop elicitation, here are the key quality requirements:\n\n");

        for (WorkshopAttribute attr : attributes) {
            sb.append(String.format("**%s** (%s, importance %s/10):\n",
                    attr.getName(), attr.getCategory(), attr.getImportance()));

            String sjStr = attr.getScenarioJson();
            if (sjStr != null && !sjStr.isBlank()) {
                try {
                    JsonNode sc = objectMapper.readTree(sjStr);
                    String stimulus = sc.path("stimulus").asText("");
                    String response = sc.path("response").asText("");
                    String measure  = sc.path("response_measure").asText("");
                    if (!stimulus.isBlank()) {
                        sb.append("When ").append(stimulus).append(", ");
                    }
                    if (!response.isBlank()) {
                        sb.append("the system should ").append(response);
                    }
                    if (!measure.isBlank()) {
                        sb.append(", measured by: ").append(measure);
                    }
                    sb.append(".\n");
                } catch (Exception ignored) {}
            }
            sb.append("\n");
        }

        sb.append("Please design an architecture that satisfies these quality attributes.")
          .append(" Prioritise trade-offs among the top-ranked attributes.");

        return sb.toString();
    }
}
