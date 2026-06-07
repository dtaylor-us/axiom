package com.archon.api.service;

import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.model.MessageRole;
import com.archon.api.dto.AgentRequest;
import com.archon.api.dto.AgentResponse;
import com.archon.api.dto.ChatRequest;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.publisher.SynchronousSink;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

@Service @RequiredArgsConstructor @Slf4j
public class ChatService {

    private final ConversationService conversationService;
    private final AgentBridgeService agentBridgeService;
    private final ArchitectureOutputService architectureOutputService;
    private final GovernanceService governanceService;
    private final TacticsService tacticsService;
    private final BuyVsBuildService buyVsBuildService;
    private final UsageService usageService;
    private final PipelineRunService pipelineRunService;
    private final PipelineRunBroadcaster pipelineRunBroadcaster;
    private final ObjectMapper objectMapper;

    public Flux<AgentResponse> streamChat(ChatRequest request, String userId) {

        Conversation conversation = conversationService.resolveConversation(
                request.getConversationId(), userId, request.getMessage());

        conversationService.saveMessage(
                conversation, MessageRole.USER, request.getMessage(), null);

        AgentRequest agentRequest = AgentRequest.builder()
                .conversationId(conversation.getId().toString())
                .userMessage(request.getMessage())
                .mode(request.getMode().name())
                .history(conversationService.getRecentMessages(
                             conversation.getId(), 20))
                .build();

        AtomicReference<StringBuilder> buffer =
                new AtomicReference<>(new StringBuilder());
        AtomicReference<String> structuredOutput = new AtomicReference<>();
        AtomicReference<Map<String, Object>> structuredMap = new AtomicReference<>();
        AtomicReference<Map<String, Object>> completePayload = new AtomicReference<>();
        AtomicReference<UUID> runIdRef = new AtomicReference<>();
        AtomicReference<String> lastStageRef = new AtomicReference<>();
        AtomicBoolean sawCompleteEvent = new AtomicBoolean(false);

        // Use switchOnFirst to defer pipeline run creation until the agent emits
        // its first successful signal. This preserves the ability for the
        // GlobalExceptionHandler to return 503 when the agent is unavailable:
        // if the agent errors before emitting any element, switchOnFirst propagates
        // the error without committing an HTTP 200 response.
        return agentBridgeService.stream(agentRequest)
                .switchOnFirst((signal, flux) -> {
                    if (signal.isOnError()) {
                        // Agent failed immediately — propagate so the exception
                        // handler can still map it to 503 SERVICE_UNAVAILABLE.
                        return flux;
                    }

                    // Agent is responsive — create the durable pipeline run record.
                    pipelineRunService.createRun(conversation, 0).ifPresent(id -> {
                        runIdRef.set(id);
                        try {
                            AgentResponse rc = new AgentResponse();
                            rc.setType(AgentResponse.EventType.RUN_CREATED);
                            rc.setPayload(Map.of("runId", id.toString()));
                            String json = objectMapper.writeValueAsString(rc);
                            pipelineRunService.appendEvent(
                                    id, AgentResponse.EventType.RUN_CREATED.name(), null, json);
                        } catch (Exception e) {
                            log.warn("Failed to persist RUN_CREATED event. conversation={}",
                                    conversation.getId(), e);
                        }
                    });

                    AgentResponse runCreatedEvent = new AgentResponse();
                    runCreatedEvent.setType(AgentResponse.EventType.RUN_CREATED);
                    runCreatedEvent.setConversationId(conversation.getId().toString());
                    runCreatedEvent.setPayload(Map.of(
                            "runId", runIdRef.get() != null ? runIdRef.get().toString() : ""));

                    // Apply per-chunk and on-complete hooks to the full stream
                    // (flux includes the first element that was peeked by switchOnFirst).
                    Flux<AgentResponse> monitoredFlux = flux
                            .<AgentResponse>handle((chunk, sink) -> validateAndAuditAgentEvent(
                                    chunk, conversation.getId(), userId, sink))
                            .doOnNext(chunk -> {
                                UUID runId = runIdRef.get();
                                if (runId != null) {
                                    try {
                                        String json = objectMapper.writeValueAsString(chunk);
                                        pipelineRunService.appendEvent(
                                                runId,
                                                chunk.getType() != null ? chunk.getType().name() : "UNKNOWN",
                                                chunk.getStage(),
                                                json
                                        );
                                        pipelineRunBroadcaster.publish(runId, json);
                                        if (chunk.getType() == AgentResponse.EventType.STAGE_COMPLETE
                                                && chunk.getStage() != null) {
                                            pipelineRunService.updateLastStage(runId, chunk.getStage());
                                        }
                                        if (chunk.getType() == AgentResponse.EventType.ERROR) {
                                            pipelineRunService.failRun(runId, chunk.getStage(), chunk.getContent());
                                            pipelineRunBroadcaster.complete(runId);
                                        }
                                    } catch (Exception e) {
                                        log.warn("Failed to persist pipeline event. conversation={}",
                                                conversation.getId(), e);
                                    }
                                }
                                if (chunk.getStage() != null && !chunk.getStage().isBlank()) {
                                    lastStageRef.set(chunk.getStage());
                                }
                                if (chunk.getType() == AgentResponse.EventType.CHUNK
                                        && chunk.getContent() != null) {
                                    buffer.get().append(chunk.getContent());
                                }
                                if (chunk.getType() == AgentResponse.EventType.COMPLETE
                                        && chunk.getPayload() != null) {
                                    sawCompleteEvent.set(true);
                                    try {
                                        structuredOutput.set(
                                                objectMapper.writeValueAsString(chunk.getPayload()));
                                        // Capture full COMPLETE payload for token_usage extraction
                                        if (chunk.getPayload() instanceof Map<?, ?> payloadMap) {
                                            @SuppressWarnings("unchecked")
                                            Map<String, Object> pm = (Map<String, Object>) payloadMap;
                                            completePayload.set(pm);
                                            @SuppressWarnings("unchecked")
                                            Map<String, Object> so = (Map<String, Object>)
                                                    pm.get("structured_output");
                                            if (so != null) {
                                                structuredMap.set(so);
                                            }
                                        }
                                    } catch (JsonProcessingException e) {
                                        log.warn("Failed to serialize structured output", e);
                                    }
                                }
                            })
                            .doOnError(throwable -> {
                                UUID runId = runIdRef.get();
                                if (runId == null) {
                                    return;
                                }
                                String errorMessage = "Agent stream terminated before COMPLETE: "
                                        + throwable.getClass().getSimpleName()
                                        + " - "
                                        + (throwable.getMessage() != null
                                        ? throwable.getMessage()
                                        : "no message");
                                pipelineRunService.failRun(runId, lastStageRef.get(), errorMessage);
                                pipelineRunBroadcaster.complete(runId);
                                log.warn(
                                        "Pipeline run failed due to stream error. runId={} stage={} error={}",
                                        runId,
                                        lastStageRef.get(),
                                        errorMessage
                                );
                            })
                            .doOnComplete(() -> {
                                // Schedule blocking JPA persistence off the reactive thread
                                // so the SSE completion signal propagates immediately.
                                CompletableFuture.runAsync(() -> {
                                    try {
                                        String text = buffer.get().toString();
                                        if (!text.isBlank()) {
                                            conversationService.saveMessage(
                                                    conversation, MessageRole.ASSISTANT,
                                                    text, structuredOutput.get());
                                        }
                                        // Persist architecture output if present
                                        Map<String, Object> so = structuredMap.get();
                                        if (so != null && so.containsKey("architecture_design")) {
                                            architectureOutputService.saveFromStructuredOutput(
                                                    conversation.getId(), so);
                                        }
                                        // Persist FMEA risks if present
                                        if (so != null && so.containsKey("fmea_risks")) {
                                            @SuppressWarnings("unchecked")
                                            var fmeaRisks = (java.util.List<Map<String, Object>>)
                                                    so.get("fmea_risks");
                                            if (fmeaRisks != null && !fmeaRisks.isEmpty()) {
                                                governanceService.saveFmeaRisks(conversation.getId(), fmeaRisks);
                                            }
                                        }
                                        // Persist tactics if present (stage 4b)
                                        if (so != null && so.containsKey("tactics")) {
                                            try {
                                                @SuppressWarnings("unchecked")
                                                var tactics = (java.util.List<Map<String, Object>>)
                                                        so.get("tactics");
                                                if (tactics != null && !tactics.isEmpty()) {
                                                    tacticsService.saveTactics(conversation.getId(), tactics);
                                                }
                                            } catch (Exception e) {
                                                log.warn("Failed to persist tactics for conversation={}",
                                                        conversation.getId(), e);
                                            }
                                        }
                                        // Persist buy-vs-build decisions if present (stage 6b)
                                        if (so != null && so.containsKey("buy_vs_build_analysis")) {
                                            try {
                                                @SuppressWarnings("unchecked")
                                                var decisions = (java.util.List<Map<String, Object>>)
                                                        so.get("buy_vs_build_analysis");
                                                if (decisions != null && !decisions.isEmpty()) {
                                                    buyVsBuildService.saveDecisions(conversation, decisions);
                                                }
                                            } catch (Exception e) {
                                                log.warn("Failed to persist buy-vs-build decisions for conversation={}",
                                                        conversation.getId(), e);
                                            }
                                        }
                                        // Persist governance report if present
                                        if (so != null && so.containsKey("governance_score")) {
                                            governanceService.saveGovernanceReport(conversation.getId(), so);
                                        }
                                        // Persist token usage — lives at the COMPLETE payload level,
                                        // not inside structured_output.
                                        Map<String, Object> cp = completePayload.get();
                                        if (cp != null) {
                                            persistTokenUsage(conversation.getId(), cp);
                                        }
                                        // Mark pipeline run complete
                                        UUID runId = runIdRef.get();
                                        if (runId != null && so != null) {
                                            try {
                                                Integer govScore = (so.get("governance_score") instanceof Number n)
                                                        ? n.intValue() : null;
                                                String confidence = so.get("governance_score_confidence") != null
                                                        ? so.get("governance_score_confidence").toString()
                                                        : null;
                                                pipelineRunService.completeRun(
                                                        runId, govScore, confidence, false, null, null, null);
                                                pipelineRunBroadcaster.complete(runId);
                                            } catch (Exception e) {
                                                log.warn("Failed to complete pipeline run. runId={}", runId, e);
                                            }
                                            } else if (runId != null && !sawCompleteEvent.get()) {
                                                String incompleteMessage = "Agent stream ended without COMPLETE event";
                                                pipelineRunService.failRun(
                                                    runId,
                                                    lastStageRef.get(),
                                                    incompleteMessage
                                                );
                                                pipelineRunBroadcaster.complete(runId);
                                                log.warn(
                                                    "Pipeline run marked failed because stream completed without COMPLETE. "
                                                        + "runId={} stage={}",
                                                    runId,
                                                    lastStageRef.get()
                                                );
                                        }
                                        log.info("Stream complete conversation={}", conversation.getId());
                                    } catch (Exception e) {
                                        log.warn("Post-stream persistence failed for conversation={}",
                                                conversation.getId(), e);
                                    }
                                });
                            });

                    auditEventWrite(
                            conversation.getId(),
                            userId,
                            AgentResponse.EventType.RUN_CREATED.name(),
                            null
                    );
                    return Flux.concat(Mono.just(runCreatedEvent), monitoredFlux);
                });
    }

    /**
     * Validates event ownership before an agent event reaches SSE forwarding.
     */
    void validateAndAuditAgentEvent(
            AgentResponse event,
            UUID conversationId,
            String userId,
            SynchronousSink<AgentResponse> sink
    ) {
        String eventConversationId = extractConversationId(event);
        if (!eventConversationId.isEmpty()
                && !eventConversationId.equals(conversationId.toString())) {
            log.error(
                    "ROUTING_VIOLATION: event from wrong conversation discarded. "
                            + "expected={} received={} eventType={} stage={}",
                    conversationId,
                    eventConversationId,
                    event.getType() != null ? event.getType().name() : "",
                    event.getStage() != null ? event.getStage() : ""
            );
            return;
        }

        auditEventWrite(
                conversationId,
                userId,
                event.getType() != null ? event.getType().name() : "",
                event.getStage() != null ? event.getStage() : ""
        );
        sink.next(event);
    }

    /**
     * Logs every event that is about to be forwarded through the SSE stream.
     */
    void auditEventWrite(
            UUID conversationId,
            String userId,
            String eventType,
            String stageName
    ) {
        log.info(
                "SSE_AUDIT write. conversationId={} userId={} "
                        + "eventType={} stage={} emitterCount={} "
                        + "threadId={}",
                conversationId,
                userId,
                eventType,
                stageName,
                pipelineRunBroadcaster.activeCount(),
                Thread.currentThread().getId()
        );
    }

    private String extractConversationId(AgentResponse event) {
        if (event.getConversationId() != null && !event.getConversationId().isBlank()) {
            return event.getConversationId();
        }
        if (event.getPayload() instanceof Map<?, ?> payload) {
            Object payloadConversationId = payload.get("conversationId");
            if (payloadConversationId != null) {
                return payloadConversationId.toString();
            }
        }
        return "";
    }

    /**
     * Extract and persist token_usage from the COMPLETE payload.
     * Best-effort — never throws.
     */
    @SuppressWarnings("unchecked")
    private void persistTokenUsage(UUID conversationId,
                                   Map<String, Object> payload) {
        try {
            Object tu = payload.get("token_usage");
            if (tu instanceof Map<?, ?> tokenUsageMap) {
                usageService.saveFromPayload(
                        conversationId,
                        (Map<String, Object>) tokenUsageMap);
            }
        } catch (Exception e) {
            log.warn("Failed to persist token usage for conversation={}",
                     conversationId, e);
        }
    }
}
