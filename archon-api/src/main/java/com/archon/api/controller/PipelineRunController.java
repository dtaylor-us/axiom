package com.archon.api.controller;

import com.archon.api.dto.PipelineRunStatusDto;
import com.archon.api.domain.model.PipelineRunStatus;
import com.archon.api.service.ConversationService;
import com.archon.api.service.PipelineRunBroadcaster;
import com.archon.api.service.PipelineRunService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * Durable run lifecycle endpoints.
 *
 * <p>Allows clients to check run state and replay persisted SSE events after disconnects.</p>
 */
@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
@Slf4j
public class PipelineRunController {

    private final ConversationService conversationService;
    private final PipelineRunService pipelineRunService;
    private final PipelineRunBroadcaster pipelineRunBroadcaster;

    /**
     * Returns status and metadata of the most recent run for a conversation.
     */
    @GetMapping("/{conversationId}/run/status")
    public ResponseEntity<PipelineRunStatusDto> getRunStatus(
            @PathVariable UUID conversationId,
            @AuthenticationPrincipal String userId
    ) {
        conversationService.getConversation(conversationId, userId);

        return pipelineRunService.findLatestRun(conversationId)
                .map(run -> ResponseEntity.ok(new PipelineRunStatusDto(
                        run.getId(),
                        conversationId,
                        run.getStatus() != null ? run.getStatus().name() : null,
                        run.getLastStageCompleted(),
                        run.getStartedAt(),
                        run.getCompletedAt(),
                        run.getGovernanceScore(),
                        run.getGovernanceConfidence(),
                        run.getHasGaps(),
                        run.getGapSummary(),
                        run.getErrorStage(),
                        run.getErrorMessage(),
                        pipelineRunService.getEventCount(run.getId())
                )))
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Reattaches to a run: replays persisted events then closes.
     *
     * <p>Phase 1 implementation provides replay. Live continuation is handled by the primary stream.</p>
     */
    @GetMapping(
            value = "/{conversationId}/run/stream",
            produces = MediaType.TEXT_EVENT_STREAM_VALUE
    )
    public SseEmitter reattachStream(
            @PathVariable UUID conversationId,
            @RequestParam(required = false) UUID runId,
            @AuthenticationPrincipal String userId
    ) {
        conversationService.getConversation(conversationId, userId);

        UUID effectiveRunId = runId != null
                ? runId
                : pipelineRunService.findLatestRun(conversationId)
                .map(r -> r.getId())
                .orElse(null);

        if (effectiveRunId == null) {
            throw new IllegalArgumentException("No run found for conversation");
        }

        SseEmitter emitter = new SseEmitter(600_000L);
        CompletableFuture.runAsync(() -> {
            try {
                for (var ev : pipelineRunService.getEvents(effectiveRunId)) {
                    if (ev.getPayload() != null) {
                        emitter.send(SseEmitter.event().data(ev.getPayload(), MediaType.APPLICATION_JSON));
                    }
                }
                pipelineRunService.getRun(effectiveRunId).ifPresentOrElse(run -> {
                    if (run.getStatus() == PipelineRunStatus.RUNNING) {
                        // Continue live streaming by registering for new events.
                        pipelineRunBroadcaster.register(effectiveRunId, emitter);
                    } else {
                        emitter.complete();
                    }
                }, emitter::complete);
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        });

        return emitter;
    }
}

