package com.memoria.api.repository;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.ArchitectureDecision;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ArchitectureDecisionRepository extends JpaRepository<ArchitectureDecision, UUID> {
    List<ArchitectureDecision> findByProjectIdOrderByAdrNumberAsc(UUID projectId);

    @Query("""
            SELECT a
            FROM ArchitectureDecision a
            WHERE a.project.id = :projectId
              AND (:status IS NULL OR a.status = :status)
              AND (:query IS NULL
                OR LOWER(a.title) LIKE CONCAT('%', :query, '%')
                OR LOWER(a.context) LIKE CONCAT('%', :query, '%')
                OR LOWER(a.decision) LIKE CONCAT('%', :query, '%')
                OR LOWER(COALESCE(a.consequences, '')) LIKE CONCAT('%', :query, '%')
                OR LOWER(COALESCE(a.alternativesConsidered, '')) LIKE CONCAT('%', :query, '%'))
            ORDER BY a.adrNumber ASC
            """)
    List<ArchitectureDecision> searchByProjectId(
            @Param("projectId") UUID projectId,
            @Param("status") AdrStatus status,
            @Param("query") String query);

    @Query("SELECT MAX(a.adrNumber) FROM ArchitectureDecision a WHERE a.project.id = :projectId")
    Optional<Integer> findMaxAdrNumberByProjectId(@Param("projectId") UUID projectId);
}
