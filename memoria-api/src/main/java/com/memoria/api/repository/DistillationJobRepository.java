package com.memoria.api.repository;

import com.memoria.api.domain.model.DistillationJob;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DistillationJobRepository extends JpaRepository<DistillationJob, UUID> {
    List<DistillationJob> findByProjectIdOrderByCreatedAtDesc(UUID projectId);
    Optional<DistillationJob> findTopByProjectIdOrderByCreatedAtDesc(UUID projectId);
}
