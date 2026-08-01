package com.archon.api.workshop.service;

import com.archon.api.domain.model.Conversation;
import com.archon.api.service.ConversationService;
import com.archon.api.workshop.domain.model.WorkshopAttribute;
import com.archon.api.workshop.domain.model.WorkshopMessage;
import com.archon.api.workshop.domain.model.WorkshopSession;
import com.archon.api.workshop.domain.repository.WorkshopAttributeRepository;
import com.archon.api.workshop.domain.repository.WorkshopMessageRepository;
import com.archon.api.workshop.domain.repository.WorkshopSessionRepository;
import com.archon.api.workshop.dto.AttributePreviewDto;
import com.archon.api.workshop.dto.AttributeSummaryDto;
import com.archon.api.workshop.dto.ArchitectureImplicationDto;
import com.archon.api.workshop.dto.GenerationReadinessDto;
import com.archon.api.workshop.dto.HighValueGapDto;
import com.archon.api.workshop.dto.AttributeResolutionDto;
import com.archon.api.workshop.dto.QualityAttributeDto;
import com.archon.api.workshop.dto.ResolvedAnswerDto;
import com.archon.api.workshop.dto.UtilityTreeDto;
import com.archon.api.workshop.dto.UtilityTreeNodeDto;
import com.archon.api.workshop.dto.WorkshopGenerationResponseDto;
import com.archon.api.workshop.dto.WorkshopSessionDto;
import com.archon.api.workshop.client.WorkshopAgentClient;
import com.archon.api.workshop.dto.WorkshopScenarioDto;
import com.archon.api.workshop.dto.WorkshopTurnResponseDto;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
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
    private static final int DUPLICATE_PIPELINE_WINDOW_SECONDS = 60;

    private static final Set<String> OPERATIONAL_METRIC_SIGNALS = Set.of(
            "ms",
            "milliseconds",
            "seconds",
            "minutes",
            "%",
            "percent",
            "per second",
            "per minute",
            "requests/second",
            "requests per second",
            "transactions/second",
            "transactions per second",
            "rps",
            "tps",
            "requests",
            "transactions",
            "availability",
            "uptime",
            "recovery",
            "latency",
            "throughput",
            "sla"
    );

    private static final Set<String> PROHIBITED_MECHANISM_TERMS = Set.of(
            "async worker pool",
            "consensus protocol",
            "circuit breaker",
            "fallback handler",
            "local state store",
            "event sourcing",
            "saga pattern",
            "cqrs",
            "outbox pattern",
            "distributed lock",
            "message queue",
            "message broker",
            "load balancer",
            "api gateway",
            "service mesh",
            "kafka",
            "redis",
            "rabbitmq",
            "postgresql",
            "kubernetes",
            "docker"
    );

    /**
     * Returned by {@link WorkshopService#sendToPipeline} so the caller can both
     * navigate to the new conversation and kick off the pipeline stream with
     * the requirements text as the initial user message.
     *
     * @param conversationId the newly created conversation's UUID
     * @param initialMessage the formatted requirements text; must be sent via
     *                       the SSE chat stream so the pipeline processes it
     */
    public record SendToPipelineResult(UUID conversationId, String initialMessage) {}

    private record OpenQuestionForPipeline(
            String question,
            String priority,
            String architecturalImpact
    ) {}

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
                throw new com.archon.api.workshop.exception.WorkshopTurnTimeoutException(sessionId);
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

        // Persist utility_tree and architecture_implications when the agent generates them.
        persistUtilityArtifacts(session, updatedContext);

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
     * Returns the utility tree for a session.
     *
     * @throws ResponseStatusException 404 when no utility tree has been generated yet.
     */
    @Transactional(readOnly = true)
    public UtilityTreeDto getUtilityTree(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);
        String treeJson = session.getUtilityTree();
        if (treeJson == null || treeJson.isBlank()) {
            throw new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.NOT_FOUND,
                    "Utility tree not yet generated for session " + sessionId);
        }
        try {
            JsonNode tree = objectMapper.readTree(treeJson);
            return toUtilityTreeDto(tree);
        } catch (Exception e) {
            log.error("Could not parse utility_tree for session {}", sessionId, e);
            throw new org.springframework.web.server.ResponseStatusException(
                    org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                    "Could not parse utility tree");
        }
    }

    /**
     * Returns the list of architectural implications for a session.
     *
     * Returns an empty list when no implications have been generated yet.
     */
    @Transactional(readOnly = true)
    public List<ArchitectureImplicationDto> getImplications(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);
        String implJson = session.getArchitectureImplications();
        if (implJson == null || implJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode implArray = objectMapper.readTree(implJson);
            if (!implArray.isArray()) {
                return List.of();
            }
            List<ArchitectureImplicationDto> result = new ArrayList<>();
            for (JsonNode node : implArray) {
                result.add(toImplicationDto(node));
            }
            return result;
        } catch (Exception e) {
            log.error("Could not parse architecture_implications for session {}", sessionId, e);
            return List.of();
        }
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
            if (!containsOperationalMetric(meas)) {
                return "needs_operational_metric";
            }
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

    private static boolean containsOperationalMetric(String responseMeasure) {
        String lower = responseMeasure == null ? "" : responseMeasure.toLowerCase();
        return OPERATIONAL_METRIC_SIGNALS.stream().anyMatch(lower::contains);
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
    public SendToPipelineResult sendToPipeline(UUID sessionId, String userId) {
        WorkshopSession session = requireSession(sessionId, userId);

        if (session.getPipelineConversationId() != null
                && session.getPipelineSentAt() != null
                && session.getPipelineSentAt().isAfter(Instant.now()
                .minus(DUPLICATE_PIPELINE_WINDOW_SECONDS, ChronoUnit.SECONDS))) {
            log.info(
                    "Duplicate send-to-pipeline suppressed server-side. "
                    + "sessionId={} existingConversationId={}",
                    sessionId, session.getPipelineConversationId());
            return new SendToPipelineResult(
                    session.getPipelineConversationId(),
                    formatExistingPipelineMessage(session));
        }

        // Complete the session if not already done
        if (!session.isComplete()) {
            completeSession(sessionId, userId);
            // Re-fetch to get updated complete flag
            session = requireSession(sessionId, userId);
        }

        // Fetch confirmed attributes
        List<WorkshopAttribute> attrs =
                attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(sessionId);

        // Include "must" implications as non-negotiable constraints in the pipeline input.
        List<ArchitectureImplicationDto> implications =
                parseImplicationsForPipeline(session);

        UtilityTreeDto utilityTree = parseUtilityTreeForPipeline(session);
        List<WorkshopScenarioDto> scenarios = extractScenariosFromContext(session.getContextJson());
        List<OpenQuestionForPipeline> openQuestions =
                extractOpenQuestionsFromContext(session.getContextJson());
        String requirementsText = formatWorkshopOutputAsRequirements(
                session.getSystemName(),
                attrs,
                implications,
                utilityTree,
                scenarios,
                openQuestions);

        // Create an empty conversation — the message is NOT saved here.
        // The caller must submit requirementsText via the SSE chat stream so
        // the pipeline processes it and generates a response. Saving the message
        // here without running the pipeline would leave the conversation in a
        // perpetually-pending state with no agent reply.
        Conversation conversation = conversationService.resolveConversation(
                null, userId, requirementsText);

        log.info("Workshop session {} bridged to conversation {} for user {}",
                sessionId, conversation.getId(), userId);

        session.setPipelineConversationId(conversation.getId());
        session.setPipelineSentAt(Instant.now());
        sessionRepo.save(session);

        return new SendToPipelineResult(conversation.getId(), requirementsText);
    }

    private String formatExistingPipelineMessage(WorkshopSession session) {
        List<WorkshopAttribute> attrs =
                attributeRepo.findBySessionIdOrderByImportanceAscNameAsc(session.getId());
        List<ArchitectureImplicationDto> implications = parseImplicationsForPipeline(session);
        UtilityTreeDto utilityTree = parseUtilityTreeForPipeline(session);
        List<WorkshopScenarioDto> scenarios = extractScenariosFromContext(session.getContextJson());
        List<OpenQuestionForPipeline> openQuestions =
                extractOpenQuestionsFromContext(session.getContextJson());
        return formatWorkshopOutputAsRequirements(
                session.getSystemName(),
                attrs,
                implications,
                utilityTree,
                scenarios,
                openQuestions);
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
    public List<com.archon.api.workshop.dto.WorkshopMessageDto> getMessages(
            UUID sessionId, String userId) {
        requireSession(sessionId, userId);
        return messageRepo.findBySessionIdOrderByTurnNumberAsc(sessionId)
                .stream()
                .map(m -> new com.archon.api.workshop.dto.WorkshopMessageDto(
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
     * Extracts utility_tree and architecture_implications from the updated context
     * and persists them to the session entity columns when they are present.
     */
    private void persistUtilityArtifacts(WorkshopSession session, JsonNode updatedContext) {
        JsonNode treeNode = updatedContext.path("utility_tree");
        if (!treeNode.isMissingNode() && !treeNode.isNull()) {
            try {
                session.setUtilityTree(objectMapper.writeValueAsString(treeNode));
            } catch (Exception e) {
                log.warn("Could not serialise utility_tree for session {}", session.getId(), e);
            }
        }

        JsonNode implNode = updatedContext.path("architecture_implications");
        if (implNode.isArray() && implNode.size() > 0) {
            try {
                session.setArchitectureImplications(objectMapper.writeValueAsString(implNode));
            } catch (Exception e) {
                log.warn("Could not serialise architecture_implications for session {}",
                         session.getId(), e);
            }
        }
    }

    /**
     * Maps a utility tree JSON node to its DTO.
     */
    private UtilityTreeDto toUtilityTreeDto(JsonNode tree) {
        List<UtilityTreeNodeDto> nodes = new ArrayList<>();
        JsonNode nodesNode = tree.path("nodes");
        if (nodesNode.isArray()) {
            for (JsonNode n : nodesNode) {
                nodes.add(new UtilityTreeNodeDto(
                        n.path("node_id").asText(""),
                        n.path("attribute_name").asText(""),
                        n.path("refinement").asText(""),
                        n.path("scenario_id").asText(""),
                        n.path("scenario_title").asText(""),
                        n.path("business_importance").asText(""),
                        n.path("technical_risk").asText(""),
                        n.path("priority_label").asText(""),
                        n.path("rationale").asText("")
                ));
            }
        }
        List<String> drivers = new ArrayList<>();
        JsonNode driversNode = tree.path("architectural_drivers");
        if (driversNode.isArray()) {
            for (JsonNode d : driversNode) drivers.add(d.asText());
        }
        return new UtilityTreeDto(
                tree.path("generated_at_turn").asInt(0),
                tree.path("total_scenarios").asInt(0),
                drivers,
                nodes,
                tree.path("generation_rationale").asText("")
        );
    }

    /**
     * Maps an architectural implication JSON node to its DTO.
     */
    private ArchitectureImplicationDto toImplicationDto(JsonNode node) {
        List<String> affectedQualityAttrs = parseStringListFromJsonArray(
                node.path("affected_quality_attrs"));
        return new ArchitectureImplicationDto(
                node.path("implication_id").asText(""),
                node.path("source_scenario_id").asText(""),
                node.path("source_scenario_title").asText(""),
                node.path("implication").asText(""),
                node.path("tradeoff").asText(""),
                affectedQualityAttrs,
                node.path("constraint_type").asText(""),
                node.path("constraint_classification").asText("functional_constraint"),
                node.path("strength").asText(""),
                node.path("measurable_condition").asText("")
        );
    }

    /**
     * Formats workshop output as a rich requirements brief for the reasoning
     * engine. The brief carries all known workshop evidence; the architecture
     * pipeline decides which mechanisms satisfy it.
     */
    private String formatWorkshopOutputAsRequirements(String systemName,
                                                       List<WorkshopAttribute> attributes) {
        return formatWorkshopOutputAsRequirements(
                systemName, attributes, List.of(), null, List.of(), List.of());
    }

    /**
     * Formats workshop output as a rich requirements brief for the reasoning
     * engine. Requirements that still name mechanisms are withheld from this
     * pipeline brief so the workshop never pre-decides a solution.
     */
    private String formatWorkshopOutputAsRequirements(String systemName,
                                                       List<WorkshopAttribute> attributes,
                                                       List<ArchitectureImplicationDto> implications,
                                                       UtilityTreeDto utilityTree,
                                                       List<WorkshopScenarioDto> scenarios,
                                                       List<?> openQuestions) {
        StringBuilder sb = new StringBuilder();

        appendSystemDescription(sb, systemName);
        appendArchitectureDrivers(sb, utilityTree, scenarios);
        appendQualityAttributes(sb, attributes);
        appendArchitecturalRequirements(sb, implications);
        appendTradeoffHierarchy(sb, implications);
        appendSupportingScenarios(sb, utilityTree, scenarios);
        appendOpenQuestions(sb, openQuestions);

        return sb.toString();
    }

    private void appendSystemDescription(StringBuilder sb, String systemName) {
        sb.append("# System Description\n\n");
        sb.append(systemName == null || systemName.isBlank()
                ? "Unspecified workshop system"
                : systemName);
        sb.append("\n\n");
    }

    private void appendArchitectureDrivers(StringBuilder sb,
                                           UtilityTreeDto utilityTree,
                                           List<WorkshopScenarioDto> scenarios) {
        sb.append("# Architecture Drivers\n\n");
        sb.append("The following scenarios are the primary drivers of architecture decisions. ");
        sb.append("They combine high business importance with high technical risk.\n\n");

        Set<String> driverIds = architecturalDriverIds(utilityTree);
        scenarios.stream()
                .filter(s -> driverIds.contains(s.scenarioId()))
                .forEach(s -> appendScenario(sb, s, "Driver"));
    }

    private void appendQualityAttributes(StringBuilder sb,
                                         List<WorkshopAttribute> attributes) {
        sb.append("# Quality Attributes\n\n");
        sb.append("All quality attributes identified in the workshop. ");
        sb.append("The reasoning engine must address all of these, not only ");
        sb.append("the architectural drivers.\n\n");

        for (WorkshopAttribute attr : attributes) {
            sb.append("## ").append(nullToEmpty(attr.getName()))
                    .append(" [").append(nullToEmpty(attr.getConfidence()).toUpperCase())
                    .append("]\n");
            if (attr.getDescription() != null && !attr.getDescription().isBlank()) {
                sb.append(attr.getDescription()).append("\n");
            }
            appendAttributeScenario(sb, attr);
            appendFirstListValue(sb, "Evidence", parseStringList(attr.getEvidenceQuotes()), true);
            appendFirstListValue(sb, "Still uncertain", parseStringList(attr.getOpenQuestions()), false);
            sb.append("\n");
        }
    }

    private void appendAttributeScenario(StringBuilder sb, WorkshopAttribute attr) {
        String scenarioJson = attr.getScenarioJson();
        if (scenarioJson == null || scenarioJson.isBlank()) {
            return;
        }
        try {
            JsonNode sc = objectMapper.readTree(scenarioJson);
            String responseMeasure = sc.path("response_measure").asText("");
            String stimulus = sc.path("stimulus").asText("");
            String response = sc.path("response").asText("");
            if (!responseMeasure.isBlank()) {
                sb.append("Measurable target: ").append(responseMeasure).append("\n");
            }
            if (!stimulus.isBlank()) {
                sb.append("Scenario: When ").append(stimulus.toLowerCase());
                if (!response.isBlank()) {
                    sb.append(", the system must ").append(response.toLowerCase());
                }
                sb.append(".\n");
            }
        } catch (Exception e) {
            log.warn("Could not parse attribute scenario for pipeline formatting attr={}",
                    attr.getAttributeId(), e);
        }
    }

    private void appendArchitecturalRequirements(StringBuilder sb,
                                                 List<ArchitectureImplicationDto> implications) {
        List<ArchitectureImplicationDto> safeImplications = mechanismFreeImplications(implications);
        if (safeImplications.isEmpty()) {
            return;
        }

        sb.append("# Architectural Requirements\n\n");
        sb.append("These requirements are derived from scenarios and must be satisfied ");
        sb.append("by the architecture. They state what must be true, not how to ");
        sb.append("achieve it. The choice of mechanism belongs to the architecture ");
        sb.append("generation stage.\n\n");

        safeImplications.stream()
                .filter(i -> "must".equals(i.strength()))
                .forEach(i -> appendRequirement(sb, i));
        safeImplications.stream()
                .filter(i -> "should".equals(i.strength()))
                .forEach(i -> appendRequirement(sb, i));
    }

    private void appendRequirement(StringBuilder sb,
                                   ArchitectureImplicationDto implication) {
        sb.append("## [")
                .append(nullToEmpty(implication.constraintClassification())
                        .replace("_", " ")
                        .toUpperCase())
                .append("] ")
                .append(implication.constraintType())
                .append("\n");
        sb.append(implication.implication()).append("\n");
        if (!nullToEmpty(implication.measurableCondition()).isBlank()) {
            sb.append("Measurable condition: ")
                    .append(implication.measurableCondition()).append("\n");
        }
        if (!nullToEmpty(implication.sourceScenarioTitle()).isBlank()) {
            sb.append("Source: ").append(implication.sourceScenarioTitle()).append("\n");
        }
        if (!implication.affectedQualityAttrs().isEmpty()) {
            sb.append("Quality attributes: ")
                    .append(String.join(", ", implication.affectedQualityAttrs()))
                    .append("\n");
        }
        sb.append("\n");
    }

    private void appendTradeoffHierarchy(StringBuilder sb,
                                         List<ArchitectureImplicationDto> implications) {
        List<ArchitectureImplicationDto> mustImplications = mechanismFreeImplications(implications)
                .stream()
                .filter(i -> "must".equals(i.strength()))
                .filter(i -> !nullToEmpty(i.tradeoff()).isBlank())
                .toList();
        if (mustImplications.isEmpty()) {
            return;
        }

        sb.append("# Tradeoff Hierarchy\n\n");
        sb.append("The following tradeoffs are explicit. The reasoning engine must ");
        sb.append("honour these priorities when design decisions create tension ");
        sb.append("between quality attributes.\n\n");
        mustImplications.forEach(i -> sb.append("- ").append(i.tradeoff()).append("\n"));
        sb.append("\n");
    }

    private void appendSupportingScenarios(StringBuilder sb,
                                           UtilityTreeDto utilityTree,
                                           List<WorkshopScenarioDto> scenarios) {
        sb.append("# Supporting Scenarios\n\n");
        Set<String> writtenScenarioIds = architecturalDriverIds(utilityTree);
        scenarios.stream()
                .filter(s -> !writtenScenarioIds.contains(s.scenarioId()))
                .filter(s -> !"aspirational".equals(s.completeness()))
                .forEach(s -> {
                    appendScenario(sb, s, null);
                    writtenScenarioIds.add(s.scenarioId());
                });
    }

    private void appendOpenQuestions(StringBuilder sb, List<?> openQuestions) {
        if (openQuestions.isEmpty()) {
            return;
        }
        sb.append("# Open Questions\n\n");
        sb.append("Grouped by architectural impact on the requirements:\n\n");

        List<OpenQuestionForPipeline> questions = normaliseOpenQuestions(openQuestions);
        List<OpenQuestionForPipeline> blocking = questions.stream()
                .filter(q -> q.architecturalImpact().startsWith("blocks"))
                .toList();
        if (!blocking.isEmpty()) {
            sb.append("## Blocking — must resolve before architecture\n");
            blocking.forEach(q -> sb.append("- [")
                    .append(q.priority().toUpperCase())
                    .append("] ")
                    .append(q.question())
                    .append("\n"));
            sb.append("\n");
        }

        List<OpenQuestionForPipeline> confidence = questions.stream()
                .filter(q -> !q.architecturalImpact().startsWith("blocks"))
                .toList();
        if (!confidence.isEmpty()) {
            sb.append("## Reduces confidence\n");
            confidence.forEach(q -> sb.append("- ")
                    .append(q.question())
                    .append("\n"));
        }
    }

    private void appendScenario(StringBuilder sb,
                                WorkshopScenarioDto scenario,
                                String label) {
        sb.append("## ");
        if (label != null) {
            sb.append("[").append(label).append("] ");
        }
        sb.append(scenario.title()).append("\n\n");

        appendScenarioField(sb, "Stimulus", scenario.stimulus());
        appendScenarioField(sb, "Source", scenario.source());
        appendScenarioField(sb, "Environment", scenario.environment());
        appendScenarioField(sb, "Artifact", scenario.artifact());
        appendScenarioField(sb, "Response", scenario.response());
        appendScenarioField(sb, "Response measure", scenario.responseMeasure());
        if (!scenario.exercisesAttributes().isEmpty()) {
            sb.append("Quality attributes: ")
                    .append(String.join(", ", scenario.exercisesAttributes()))
                    .append("\n");
        }
        sb.append("\n");
    }

    private void appendScenarioField(StringBuilder sb, String label, String value) {
        if (value != null && !value.isBlank()) {
            sb.append(label).append(": ").append(value).append("\n");
        }
    }

    private void appendFirstListValue(StringBuilder sb,
                                      String label,
                                      List<String> values,
                                      boolean quote) {
        if (values.isEmpty()) {
            return;
        }
        sb.append(label).append(": ");
        if (quote) {
            sb.append("\"").append(values.get(0)).append("\"");
        } else {
            sb.append(values.get(0));
        }
        sb.append("\n");
    }

    private UtilityTreeDto parseUtilityTreeForPipeline(WorkshopSession session) {
        String treeJson = session.getUtilityTree();
        if (treeJson == null || treeJson.isBlank()) {
            return null;
        }
        try {
            return toUtilityTreeDto(objectMapper.readTree(treeJson));
        } catch (Exception e) {
            log.warn("Could not parse utility_tree for sendToPipeline session {}",
                    session.getId(), e);
            return null;
        }
    }

    private List<ArchitectureImplicationDto> parseImplicationsForPipeline(
            WorkshopSession session) {
        String implJson = session.getArchitectureImplications();
        if (implJson == null || implJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode implArray = objectMapper.readTree(implJson);
            if (!implArray.isArray()) {
                return List.of();
            }
            List<ArchitectureImplicationDto> parsed = new ArrayList<>();
            for (JsonNode node : implArray) {
                parsed.add(toImplicationDto(node));
            }
            return parsed;
        } catch (Exception e) {
            log.warn("Could not parse implications for sendToPipeline session {}",
                    session.getId(), e);
            return List.of();
        }
    }

    private List<WorkshopScenarioDto> extractScenariosFromContext(String contextJson) {
        if (contextJson == null || contextJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode context = objectMapper.readTree(contextJson);
            JsonNode scenarios = context.path("scenarios");
            if (!scenarios.isArray()) {
                return List.of();
            }
            List<WorkshopScenarioDto> result = new ArrayList<>();
            for (JsonNode scenario : scenarios) {
                result.add(toScenarioDto(scenario));
            }
            return result;
        } catch (Exception e) {
            log.warn("Could not parse scenarios from workshop context", e);
            return List.of();
        }
    }

    private WorkshopScenarioDto toScenarioDto(JsonNode n) {
        String stimulus = n.path("stimulus").asText("");
        String environment = n.path("environment").asText("");
        String response = n.path("response").asText("");
        String measure = n.path("response_measure").asText("");
        String completeness = computeScenarioCompletenessFromFields(
                stimulus, environment, response, measure);
        return new WorkshopScenarioDto(
                n.path("scenario_id").asText(""),
                n.path("title").asText(""),
                stimulus,
                n.path("source").asText(""),
                environment,
                n.path("artifact").asText(""),
                response,
                measure,
                parseStringListFromJsonArray(n.path("exercises_attributes")),
                n.path("evidence_quote").asText(""),
                n.path("derived_in_turn").asInt(0),
                completeness
        );
    }

    private List<OpenQuestionForPipeline> extractOpenQuestionsFromContext(String contextJson) {
        if (contextJson == null || contextJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode context = objectMapper.readTree(contextJson);
            List<OpenQuestionForPipeline> openQuestions = new ArrayList<>();
            JsonNode attributes = context.path("attributes");
            if (attributes.isArray()) {
                for (JsonNode attribute : attributes) {
                    for (String question : parseStringListFromJsonArray(
                            attribute.path("open_questions"))) {
                        openQuestions.add(new OpenQuestionForPipeline(
                                question, "medium", "blocks_attribute_confirmation"));
                    }
                }
            }
            JsonNode gaps = context.path("gaps");
            if (gaps.isArray()) {
                for (JsonNode gap : gaps) {
                    if (!gap.path("filled").asBoolean(false)) {
                        String residual = gap.path("residual_question").asText("");
                        String description = gap.path("description").asText("");
                        String question = !residual.isBlank() ? residual : description;
                        if (!question.isBlank()) {
                            openQuestions.add(new OpenQuestionForPipeline(
                                    question,
                                    gap.path("priority").asText("medium"),
                                    gap.path("architectural_impact")
                                            .asText("informational")));
                        }
                    }
                }
            }
            return openQuestions;
        } catch (Exception e) {
            log.warn("Could not parse open questions from workshop context", e);
            return List.of();
        }
    }

    private List<OpenQuestionForPipeline> normaliseOpenQuestions(List<?> openQuestions) {
        return openQuestions.stream()
                .map(this::normaliseOpenQuestion)
                .toList();
    }

    private OpenQuestionForPipeline normaliseOpenQuestion(Object value) {
        if (value instanceof OpenQuestionForPipeline question) {
            return question;
        }
        return new OpenQuestionForPipeline(
                String.valueOf(value),
                "medium",
                "reduces_confidence");
    }

    private Set<String> architecturalDriverIds(UtilityTreeDto utilityTree) {
        if (utilityTree == null) {
            return new HashSet<>();
        }
        return new HashSet<>(utilityTree.architecturalDrivers());
    }

    private List<ArchitectureImplicationDto> mechanismFreeImplications(
            List<ArchitectureImplicationDto> implications) {
        return implications.stream()
                .filter(i -> !containsProhibitedMechanism(i.implication()))
                .toList();
    }

    private boolean containsProhibitedMechanism(String text) {
        String lower = nullToEmpty(text).toLowerCase();
        return PROHIBITED_MECHANISM_TERMS.stream().anyMatch(lower::contains);
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
