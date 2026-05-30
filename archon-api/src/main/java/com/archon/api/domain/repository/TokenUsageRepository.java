package com.archon.api.domain.repository;

import com.archon.api.domain.model.TokenUsage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface TokenUsageRepository extends JpaRepository<TokenUsage, UUID> {

    List<TokenUsage> findByConversationIdOrderByCreatedAtAsc(UUID conversationId);
}
