package com.aiarchitect.api.workshop.controller;

import com.aiarchitect.api.workshop.dto.AttributeSummaryDto;
import com.aiarchitect.api.workshop.dto.GenerationReadinessDto;
import com.aiarchitect.api.workshop.dto.QualityAttributeDto;
import com.aiarchitect.api.workshop.dto.WorkshopGenerationResponseDto;
import com.aiarchitect.api.workshop.dto.WorkshopMessageDto;
import com.aiarchitect.api.workshop.dto.WorkshopSessionDto;
import com.aiarchitect.api.workshop.dto.WorkshopScenarioDto;
import com.aiarchitect.api.workshop.dto.WorkshopTurnResponseDto;
import com.aiarchitect.api.workshop.exception.WorkshopTurnTimeoutException;
import com.aiarchitect.api.workshop.service.WorkshopService;
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
            @AuthenticationPrincipal String userId) {

        log.info("Sending workshop session {} to pipeline for user {}", id, userId);
        UUID conversationId = workshopService.sendToPipeline(id, userId);
        return ResponseEntity.ok(Map.of("conversationId", conversationId.toString()));
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
