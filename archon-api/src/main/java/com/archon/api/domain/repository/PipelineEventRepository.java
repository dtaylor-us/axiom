package com.archon.api.domain.repository;

import com.archon.api.domain.model.PipelineEvent;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface PipelineEventRepository extends JpaRepository<PipelineEvent, UUID> {

    List<PipelineEvent> findByRunIdOrderBySequenceNumAsc(UUID runId);

    int countByRunId(UUID runId);
}

