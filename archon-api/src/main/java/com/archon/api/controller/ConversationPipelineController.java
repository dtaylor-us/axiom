package com.archon.api.controller;

import com.archon.api.dto.PipelineStatusResponse;
import com.archon.api.service.ConversationService;
import com.archon.api.service.PipelineRunService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Conversation-level pipeline endpoints for progress reconstruction.
 */
@RestController
@RequestMapping("/api/v1/conversations")
@RequiredArgsConstructor
public class ConversationPipelineController {

    private final ConversationService conversationService;
    private final PipelineRunService pipelineRunService;

    /**
     * Returns the most recent pipeline run snapshot for a conversation.
     */
    @GetMapping("/{conversationId}/pipeline-status")
    public ResponseEntity<PipelineStatusResponse> getPipelineStatus(
            @PathVariable UUID conversationId,
            @AuthenticationPrincipal String userId
    ) {
        conversationService.getConversationOrForbidden(conversationId, userId);

        return pipelineRunService.findLatestRun(conversationId)
                .map(run -> {
                    List<PipelineStatusResponse.EventDto> events = pipelineRunService.getEvents(run.getId()).stream()
                            .map(event -> new PipelineStatusResponse.EventDto(
                                    event.getEventType(),
                                    event.getStageName(),
                                    event.getSequenceNum(),
                                    event.getEmittedAt(),
                                    event.getPayload()
                            ))
                            .toList();

                    StageState stageState = deriveStageState(events);
                    String lastStageCompleted = run.getLastStageCompleted() != null
                            ? run.getLastStageCompleted()
                            : stageState.lastStageCompleted();

                    PipelineStatusResponse response = new PipelineStatusResponse(
                            run.getId(),
                            run.getStatus() != null ? run.getStatus().name() : null,
                            lastStageCompleted,
                            stageState.completedStages(),
                            stageState.activeStage(),
                            events,
                            run.getGovernanceScore(),
                            Boolean.TRUE.equals(run.getHasGaps())
                    );
                    return ResponseEntity.ok(response);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    private StageState deriveStageState(List<PipelineStatusResponse.EventDto> events) {
        Set<String> completedStages = new LinkedHashSet<>();
        List<String> startedNotCompleted = new ArrayList<>();
        String lastCompleted = null;

        for (PipelineStatusResponse.EventDto event : events) {
            String stageName = event.stage();
            if (stageName == null || stageName.isBlank()) {
                continue;
            }

            if ("STAGE_START".equals(event.type())) {
                startedNotCompleted.remove(stageName);
                startedNotCompleted.add(stageName);
            }

            if ("STAGE_COMPLETE".equals(event.type())) {
                completedStages.add(stageName);
                startedNotCompleted.remove(stageName);
                lastCompleted = stageName;
            }
        }

        String activeStage = startedNotCompleted.isEmpty()
                ? null
                : startedNotCompleted.get(startedNotCompleted.size() - 1);

        return new StageState(new ArrayList<>(completedStages), activeStage, lastCompleted);
    }

    private record StageState(
            List<String> completedStages,
            String activeStage,
            String lastStageCompleted
    ) {
    }
}
