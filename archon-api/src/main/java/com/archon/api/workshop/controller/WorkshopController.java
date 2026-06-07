package com.archon.api.workshop.controller;

import com.archon.api.workshop.dto.ArchitectureImplicationDto;
import com.archon.api.workshop.dto.AttributeSummaryDto;
import com.archon.api.workshop.dto.GenerationReadinessDto;
import com.archon.api.workshop.dto.AttributeResolutionDto;
import com.archon.api.workshop.dto.QualityAttributeDto;
import com.archon.api.workshop.dto.UtilityTreeDto;
import com.archon.api.workshop.dto.WorkshopGenerationResponseDto;
import com.archon.api.workshop.dto.WorkshopMessageDto;
import com.archon.api.workshop.dto.WorkshopSessionDto;
import com.archon.api.workshop.dto.WorkshopScenarioDto;
import com.archon.api.workshop.dto.WorkshopTurnResponseDto;
import com.archon.api.workshop.exception.WorkshopTurnTimeoutException;
import com.archon.api.workshop.service.WorkshopService;
import com.github.benmanes.caffeine.cache.Cache;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * REST controller for Quality Attribute Workshop sessions.
 *
 * <p>All endpoints require a valid JWT; the userId is extracted from the
 * authentication principal — exactly as in the existing ChatController.
 *
 * <p>Base path: /api/v1/workshop/sessions
 */
@RestController
@RequestMapping("/api/v1/workshop/sessions")
@RequiredArgsConstructor
@Slf4j
public class WorkshopController {

    private final WorkshopService workshopService;
    private final Cache<String, WorkshopService.SendToPipelineResult> idempotencyCache;
    private final Object idempotencyLock = new Object();

    // ------------------------------------------------------------------
    // Request bodies
    // ------------------------------------------------------------------

    record CreateSessionRequest(
            @NotBlank(message = "systemName is required")
            String systemName) {}

    record SubmitTurnRequest(
            @NotBlank(message = "userInput is required")
            String userInput) {}

    // ------------------------------------------------------------------
    // Endpoints
    // ------------------------------------------------------------------

    /**
     * POST /api/v1/workshop/sessions
     * Creates a new workshop session.
     */
    @PostMapping
    public ResponseEntity<WorkshopSessionDto> createSession(
            @RequestBody @Valid CreateSessionRequest body,
            @AuthenticationPrincipal String userId) {

        log.info("Creating workshop session for user {} system '{}'",
                userId, body.systemName());
        WorkshopSessionDto dto = workshopService.createSession(userId, body.systemName());
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * POST /api/v1/workshop/sessions/{id}/turn
     * Submits a conversational turn to the workshop agent.
     */
    @PostMapping("/{id}/turn")
    public ResponseEntity<WorkshopTurnResponseDto> submitTurn(
            @PathVariable UUID id,
            @RequestBody @Valid SubmitTurnRequest body,
            @AuthenticationPrincipal String userId) {

        log.info("Processing workshop turn for session {} user {}", id, userId);
        WorkshopTurnResponseDto response = workshopService.processTurn(
                id, userId, body.userInput());
        return ResponseEntity.ok(response);
    }

    /**
     * GET /api/v1/workshop/sessions/{id}
     * Returns the session DTO including phase and gap completion.
     */
    @GetMapping("/{id}")
    public ResponseEntity<WorkshopSessionDto> getSession(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getSession(id, userId));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/attributes
     * Returns quality attributes; optional ?confidence= filter (confirmed/partial/weak).
     */
    @GetMapping("/{id}/attributes")
    public ResponseEntity<List<QualityAttributeDto>> getAttributes(
            @PathVariable UUID id,
            @RequestParam(required = false) String confidence,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(
                workshopService.getAttributes(id, userId, confidence));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/resolutions
     * Resolution traceability: which answers resolved which attribute questions.
     */
    @GetMapping("/{id}/resolutions")
    public ResponseEntity<List<AttributeResolutionDto>> getResolutions(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getResolutions(id, userId));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/scenarios
     * Workshop scenarios from persisted context (operational QA scenarios).
     */
    @GetMapping("/{id}/scenarios")
    public ResponseEntity<List<WorkshopScenarioDto>> getScenarios(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getScenarios(id, userId));
    }

    /**
     * POST /api/v1/workshop/sessions/{id}/complete
     * Marks the session complete; returns the structured attribute summary.
     */
    @PostMapping("/{id}/complete")
    public ResponseEntity<AttributeSummaryDto> completeSession(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        log.info("Completing workshop session {} for user {}", id, userId);
        return ResponseEntity.ok(workshopService.completeSession(id, userId));
    }

    /**
     * POST /api/v1/workshop/sessions/{id}/send-to-pipeline
     * Bridges the workshop output into the main pipeline.
     * Returns the new conversationId.
     */
    @PostMapping("/{id}/send-to-pipeline")
    public ResponseEntity<Map<String, String>> sendToPipeline(
            @PathVariable UUID id,
            @RequestHeader(value = "Idempotency-Key", required = false)
            String idempotencyKey,
            @AuthenticationPrincipal String userId) {

        String cacheKey = normaliseIdempotencyKey(idempotencyKey);
        synchronized (idempotencyLock) {
            WorkshopService.SendToPipelineResult cached = cacheKey == null
                    ? null
                    : idempotencyCache.getIfPresent(cacheKey);
            if (cached != null) {
                log.info(
                        "send-to-pipeline attempt. sessionId={} userId={} idempotencyKey={} isDuplicate=true",
                        id, userId, cacheKey);
                log.info(
                        "Duplicate send-to-pipeline suppressed. key={} sessionId={}",
                        cacheKey, id);
                return sendToPipelineResponse(cached, true);
            }

            log.info(
                    "send-to-pipeline attempt. sessionId={} userId={} idempotencyKey={} isDuplicate=false",
                    id, userId, cacheKey);
            var result = workshopService.sendToPipeline(id, userId);
            if (cacheKey != null) {
                idempotencyCache.put(cacheKey, result);
            }
            return sendToPipelineResponse(result, false);
        }
    }

    private ResponseEntity<Map<String, String>> sendToPipelineResponse(
            WorkshopService.SendToPipelineResult result,
            boolean deduplicated) {
        Map<String, String> body = deduplicated
                ? Map.of(
                        "conversationId", result.conversationId().toString(),
                        "initialMessage", result.initialMessage(),
                        "deduplicated", "true")
                : Map.of(
                        "conversationId", result.conversationId().toString(),
                        "initialMessage", result.initialMessage());
        return ResponseEntity.ok(Map.of(
                "conversationId", body.get("conversationId"),
                "initialMessage", body.get("initialMessage"),
                "deduplicated", body.getOrDefault("deduplicated", "false")));
    }

    private String normaliseIdempotencyKey(String idempotencyKey) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            return null;
        }
        return idempotencyKey.strip();
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/messages
     * Returns the conversation message history for a session, oldest first.
     */
    @GetMapping("/{id}/messages")
    public ResponseEntity<List<WorkshopMessageDto>> getMessages(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getMessages(id, userId));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/generation-readiness
     * Read-only preview of what generating attributes now would produce.
     */
    @GetMapping("/{id}/generation-readiness")
    public ResponseEntity<GenerationReadinessDto> getGenerationReadiness(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(
                workshopService.assessGenerationReadiness(id, userId));
    }

    /**
     * POST /api/v1/workshop/sessions/{id}/generate
     * Generates quality attributes from accumulated evidence; session stays active.
     */
    @PostMapping("/{id}/generate")
    public ResponseEntity<WorkshopGenerationResponseDto> generateAttributes(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.generateAttributes(id, userId));
    }

    /**
     * GET /api/v1/workshop/sessions
     * Lists all sessions for the authenticated user, most recent first.
     */
    @GetMapping
    public ResponseEntity<List<WorkshopSessionDto>> listSessions(
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.listSessions(userId));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/utility-tree
     * Returns the SEI QAW utility tree for the session.
     * Returns 404 when the utility tree has not been generated yet.
     */
    @GetMapping("/{id}/utility-tree")
    public ResponseEntity<UtilityTreeDto> getUtilityTree(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getUtilityTree(id, userId));
    }

    /**
     * GET /api/v1/workshop/sessions/{id}/implications
     * Returns architectural implications derived from driver scenarios.
     * Returns an empty array when no implications have been generated yet.
     */
    @GetMapping("/{id}/implications")
    public ResponseEntity<List<ArchitectureImplicationDto>> getImplications(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {

        return ResponseEntity.ok(workshopService.getImplications(id, userId));
    }

    // ------------------------------------------------------------------
    // Exception handlers
    // ------------------------------------------------------------------

    /**
     * Maps WorkshopTurnTimeoutException to HTTP 504 Gateway Timeout.
     *
     * <p>The {@code draft_preserved} flag tells the UI that the user's
     * input was sent before the timeout and has not been lost. The UI
     * should surface a recoverable error with a "Try Again" action.
     */
    @ExceptionHandler(WorkshopTurnTimeoutException.class)
    @ResponseStatus(HttpStatus.GATEWAY_TIMEOUT)
    public Map<String, Object> handleTurnTimeout(WorkshopTurnTimeoutException ex) {
        log.warn("Workshop turn timeout. session={}", ex.getSessionId());
        return Map.of(
                "error",          "workshop_turn_timeout",
                "message",        "The architecture agent took too long to respond. Your input was not lost.",
                "draft_preserved", true,
                "session_id",     ex.getSessionId().toString()
        );
    }
}
