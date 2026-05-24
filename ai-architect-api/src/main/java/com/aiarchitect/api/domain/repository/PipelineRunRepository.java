package com.aiarchitect.api.domain.repository;

import com.aiarchitect.api.domain.model.PipelineRun;
import com.aiarchitect.api.domain.model.PipelineRunStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PipelineRunRepository extends JpaRepository<PipelineRun, UUID> {

    Optional<PipelineRun> findTopByConversationIdAndStatusOrderByStartedAtDesc(
            UUID conversationId, PipelineRunStatus status);

    Optional<PipelineRun> findByConversationIdAndStatus(
            UUID conversationId, PipelineRunStatus status);

    List<PipelineRun> findByConversationIdOrderByStartedAtDesc(UUID conversationId);

    Optional<PipelineRun> findTopByConversationIdOrderByStartedAtDesc(UUID conversationId);
}
