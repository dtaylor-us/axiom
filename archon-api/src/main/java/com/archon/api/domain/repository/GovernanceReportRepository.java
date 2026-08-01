package com.archon.api.domain.repository;

import com.archon.api.domain.model.GovernanceReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface GovernanceReportRepository extends JpaRepository<GovernanceReport, UUID> {

    Optional<GovernanceReport> findTopByConversationIdOrderByCreatedAtDesc(
            UUID conversationId);

    Optional<GovernanceReport> findTopByConversationIdOrderByIterationDesc(
            UUID conversationId);
}
