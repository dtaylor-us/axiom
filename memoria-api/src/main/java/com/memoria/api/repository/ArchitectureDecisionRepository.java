package com.memoria.api.repository;

import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.AdrStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ArchitectureDecisionRepository extends JpaRepository<ArchitectureDecision, UUID> {
    List<ArchitectureDecision> findByProjectIdOrderByAdrNumberAsc(UUID projectId);
    List<ArchitectureDecision> findByProjectIdAndStatusInOrderByAdrNumberAsc(UUID projectId, List<AdrStatus> statuses);

    @Query("SELECT MAX(a.adrNumber) FROM ArchitectureDecision a WHERE a.project.id = :projectId")
    Optional<Integer> findMaxAdrNumberByProjectId(@Param("projectId") UUID projectId);
}
