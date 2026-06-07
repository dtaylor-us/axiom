package com.archon.api.domain.repository;

import com.archon.api.domain.model.FmeaRisk;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface FmeaRiskRepository extends JpaRepository<FmeaRisk, UUID> {

    List<FmeaRisk> findByConversationIdOrderByRpnDesc(UUID conversationId);

    List<FmeaRisk> findByConversationIdAndRpnGreaterThanEqual(
            UUID conversationId, int rpnThreshold);
}
