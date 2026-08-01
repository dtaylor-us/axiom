package com.archon.api.service;

import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.model.PipelineEvent;
import com.archon.api.domain.model.PipelineRun;
import com.archon.api.domain.model.PipelineRunStatus;
import com.archon.api.domain.repository.PipelineEventRepository;
import com.archon.api.domain.repository.PipelineRunRepository;
import com.archon.api.exception.DuplicatePipelineRunException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Manages the lifecycle of pipeline runs as durable records.
 *
 * <p>All persistence is best-effort: failures are logged but never propagated.</p>
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class PipelineRunService {

    private final PipelineRunRepository runRepository;
    private final PipelineEventRepository eventRepository;

    /**
     * Creates a new RUNNING pipeline run for a conversation.
     */
    public Optional<UUID> createRun(Conversation conversation, int iteration) {
        try {
            return Optional.of(startRun(conversation, iteration).getId());
        } catch (DuplicatePipelineRunException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to create pipeline run. conversationId={}", conversation.getId(), e);
            return Optional.empty();
        }
    }

    /**
     * Starts a durable pipeline run unless the conversation already has one running.
     *
     * @param conversation owning conversation
     * @param iteration pipeline iteration number
     * @return persisted RUNNING pipeline run
     * @throws DuplicatePipelineRunException when another run is already active
     */
    public PipelineRun startRun(Conversation conversation, int iteration) {
        Optional<PipelineRun> existingRun = runRepository.findByConversationIdAndStatus(
                conversation.getId(), PipelineRunStatus.RUNNING);

        if (existingRun.isPresent()) {
            log.error(
                    "DUPLICATE_RUN_DETECTED: pipeline already running "
                            + "for conversationId={}. runId={}. "
                            + "Rejecting duplicate start.",
                    conversation.getId(),
                    existingRun.get().getId()
            );
            throw new DuplicatePipelineRunException(
                    "A pipeline run is already active for conversation "
                            + conversation.getId() + ". Existing run: "
                            + existingRun.get().getId()
            );
        }

        PipelineRun run = PipelineRun.builder()
                .conversation(conversation)
                .iteration(iteration)
                .status(PipelineRunStatus.RUNNING)
                .startedAt(Instant.now())
                .hasGaps(false)
                .build();
        return runRepository.save(run);
    }

    /**
     * Appends an SSE event to the run's event log.
     */
    public void appendEvent(UUID runId, String eventType, String stageName, String payloadJson) {
        if (runId == null) return;
        try {
            int nextSeq = eventRepository.countByRunId(runId);
            PipelineEvent event = PipelineEvent.builder()
                    .run(runRepository.getReferenceById(runId))
                    .sequenceNum(nextSeq)
                    .eventType(eventType)
                    .stageName(stageName)
                    .payload(payloadJson)
                    .emittedAt(Instant.now())
                    .build();
            eventRepository.save(event);
        } catch (Exception e) {
            log.error("Failed to append pipeline event. runId={} type={}", runId, eventType, e);
        }
    }

    /**
     * Updates the run to COMPLETED when the COMPLETE event arrives.
     */
    public void completeRun(
            UUID runId,
            Integer governanceScore,
            String confidence,
            boolean hasGaps,
            String gapSummary,
            Integer totalTokens,
            BigDecimal estimatedCost
    ) {
        if (runId == null) return;
        try {
            runRepository.findById(runId).ifPresent(run -> {
                run.setStatus(hasGaps ? PipelineRunStatus.COMPLETED_WITH_GAPS : PipelineRunStatus.COMPLETED);
                run.setCompletedAt(Instant.now());
                run.setGovernanceScore(governanceScore);
                run.setGovernanceConfidence(confidence);
                run.setHasGaps(hasGaps);
                run.setGapSummary(gapSummary);
                run.setTotalTokens(totalTokens);
                run.setEstimatedCostUsd(estimatedCost);
                runRepository.save(run);
            });
        } catch (Exception e) {
            log.error("Failed to complete pipeline run. runId={}", runId, e);
        }
    }

    /**
     * Updates the run to FAILED when an ERROR event arrives.
     */
    public void failRun(UUID runId, String errorStage, String errorMessage) {
        if (runId == null) return;
        try {
            runRepository.findById(runId).ifPresent(run -> {
                run.setStatus(PipelineRunStatus.FAILED);
                run.setCompletedAt(Instant.now());
                run.setErrorStage(errorStage);
                run.setErrorMessage(errorMessage);
                runRepository.save(run);
            });
        } catch (Exception e) {
            log.error("Failed to mark pipeline run as failed. runId={}", runId, e);
        }
    }

    /**
     * Updates the last completed stage name on a running run.
     */
    public void updateLastStage(UUID runId, String stageName) {
        if (runId == null) return;
        try {
            runRepository.findById(runId).ifPresent(run -> {
                run.setLastStageCompleted(stageName);
                runRepository.save(run);
            });
        } catch (Exception e) {
            log.error("Failed to update last stage. runId={} stage={}", runId, stageName, e);
        }
    }

    /**
     * Returns all events for a run in sequence order.
     */
    public List<PipelineEvent> getEvents(UUID runId) {
        try {
            return eventRepository.findByRunIdOrderBySequenceNumAsc(runId);
        } catch (Exception e) {
            log.error("Failed to retrieve events. runId={}", runId, e);
            return List.of();
        }
    }

    /**
     * Returns the most recent run for a conversation regardless of status.
     */
    public Optional<PipelineRun> findLatestRun(UUID conversationId) {
        try {
            return runRepository.findTopByConversationIdOrderByStartedAtDesc(conversationId);
        } catch (Exception e) {
            log.error("Failed to find latest run. conversationId={}", conversationId, e);
            return Optional.empty();
        }
    }

    /**
     * Returns the number of persisted events for a run.
     */
    public int getEventCount(UUID runId) {
        try {
            return eventRepository.countByRunId(runId);
        } catch (Exception e) {
            log.error("Failed to count events. runId={}", runId, e);
            return 0;
        }
    }

    /**
     * Retrieves a run by id.
     */
    public Optional<PipelineRun> getRun(UUID runId) {
        try {
            return runRepository.findById(runId);
        } catch (Exception e) {
            log.error("Failed to retrieve run. runId={}", runId, e);
            return Optional.empty();
        }
    }
}
