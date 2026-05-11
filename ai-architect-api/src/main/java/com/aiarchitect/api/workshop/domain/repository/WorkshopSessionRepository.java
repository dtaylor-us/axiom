package com.aiarchitect.api.workshop.domain.repository;

import com.aiarchitect.api.workshop.domain.model.WorkshopSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for {@link WorkshopSession} entities.
 *
 * <p>All access goes through this repository. No controller or
 * other service may access the workshop_sessions table directly.</p>
 */
public interface WorkshopSessionRepository
        extends JpaRepository<WorkshopSession, UUID> {

    /**
     * Return all sessions owned by the given user, newest first.
     *
     * @param userId JWT subject claim of the requesting user
     * @return List of sessions, ordered by creation time descending
     */
    List<WorkshopSession> findByUserIdOrderByCreatedAtDesc(String userId);

    /**
     * Find a session by its ID, scoped to the owning user.
     *
     * @param id     session UUID
     * @param userId JWT subject claim of the requesting user
     * @return Optional session, empty if not found or not owned by user
     */
    Optional<WorkshopSession> findByIdAndUserId(UUID id, String userId);
}
