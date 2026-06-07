package com.archon.api.domain.repository;

import com.archon.api.domain.model.BuyVsBuildDecision;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface BuyVsBuildRepository extends JpaRepository<BuyVsBuildDecision, UUID> {

    List<BuyVsBuildDecision> findByConversationId(UUID conversationId);

    List<BuyVsBuildDecision> findByConversationIdAndRecommendation(
            UUID conversationId, String recommendation);

    List<BuyVsBuildDecision> findByConversationIdAndConflictsWithUserPreference(
            UUID conversationId, Boolean conflicts);
}

