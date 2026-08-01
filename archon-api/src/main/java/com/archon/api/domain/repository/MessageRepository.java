package com.archon.api.domain.repository;

import com.archon.api.domain.model.Message;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.UUID;

/**
 * Repository for Message entity providing database access operations.
 */
public interface MessageRepository extends JpaRepository<Message, UUID> {
    /**
     * Retrieves recent messages for a given conversation, ordered by creation date.
     *
     * @param convId the conversation UUID
     * @param pageable pagination information
     * @return list of messages ordered by creation date descending
     */
    @Query("SELECT m FROM Message m WHERE m.conversation.id = :convId " +
           "ORDER BY m.createdAt DESC")
    List<Message> findRecentByConversationId(UUID convId, Pageable pageable);
}
