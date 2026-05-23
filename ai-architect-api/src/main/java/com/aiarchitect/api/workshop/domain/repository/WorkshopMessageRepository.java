package com.aiarchitect.api.workshop.domain.repository;

import com.aiarchitect.api.workshop.domain.model.WorkshopMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

/**
 * Repository for workshop conversation messages.
 * Messages are append-only; ordered by turn number for replay.
 */
@Repository
public interface WorkshopMessageRepository extends JpaRepository<WorkshopMessage, UUID> {

    /** Returns all messages for a session in chronological order. */
    List<WorkshopMessage> findBySessionIdOrderByTurnNumberAsc(UUID sessionId);

    /** Deletes all messages for a session (used in testing). */
    void deleteBySessionId(UUID sessionId);
}
