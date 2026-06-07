package com.archon.api.domain.repository;

import com.archon.api.domain.model.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository interface for managing {@link Conversation} entities.
 * 
 * Provides database access and query operations for Conversation objects,
 * extending JpaRepository to leverage Spring Data JPA functionality.
 * 
 */
public interface ConversationRepository extends JpaRepository<Conversation, UUID> {
    
    /**
     * Retrieves all conversations for a specific user, ordered by creation date in descending order.
     * 
     * @param userId the ID of the user whose conversations are to be retrieved
     * @return a {@link List} of {@link Conversation} objects for the specified user,
     *         sorted by creation date (most recent first); empty list if no conversations found
     */
    List<Conversation> findByUserIdOrderByCreatedAtDesc(String userId);

    /**
     * Retrieves all conversations for any of the supplied ownership aliases.
     */
    List<Conversation> findByUserIdInOrderByCreatedAtDesc(List<String> userIds);
    
    /**
     * Retrieves a single conversation by its ID and user ID.
     * 
     * Ensures that a user can only retrieve their own conversations by validating
     * both the conversation ID and the owning user ID.
     * 
     * @param id the unique identifier of the conversation
     * @param userId the ID of the user who owns the conversation
     * @return an {@link Optional} containing the {@link Conversation} if found and belongs to the user,
     *         or empty if the conversation does not exist or does not belong to the specified user
     */
    Optional<Conversation> findByIdAndUserId(UUID id, String userId);

    /**
     * Retrieves a single conversation by ID for any accepted ownership alias.
     */
    Optional<Conversation> findByIdAndUserIdIn(UUID id, List<String> userIds);
}
