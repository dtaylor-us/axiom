package com.archon.api.domain.repository;

import com.archon.api.domain.model.ArchitectureOutput;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

/**
 * Repository for managing ArchitectureOutput entities.
 * Provides database access and query operations for architecture outputs.
 */
public interface ArchitectureOutputRepository extends JpaRepository<ArchitectureOutput, UUID> {

    /**
     * Retrieves the most recent ArchitectureOutput for a given conversation.
     *
     * @param conversationId the UUID of the conversation
     * @return an Optional containing the most recent ArchitectureOutput, or empty if none exists
     */
    Optional<ArchitectureOutput> findTopByConversationIdOrderByCreatedAtDesc(UUID conversationId);
}
