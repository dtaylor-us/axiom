package com.memoria.api.repository;

import com.memoria.api.domain.model.DistillationJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.EntityGraph;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DistillationJobRepository extends JpaRepository<DistillationJob, UUID> {
    @EntityGraph(attributePaths = "project")
    List<DistillationJob> findByProjectIdOrderByCreatedAtDesc(UUID projectId);

    @EntityGraph(attributePaths = "project")
    Optional<DistillationJob> findTopByProjectIdOrderByCreatedAtDesc(UUID projectId);
}
