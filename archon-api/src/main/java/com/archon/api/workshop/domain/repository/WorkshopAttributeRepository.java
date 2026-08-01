package com.archon.api.workshop.domain.repository;

import com.archon.api.workshop.domain.model.WorkshopAttribute;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for {@link WorkshopAttribute} entities.
 *
 * <p>Attributes are a denormalised mirror of the attribute list
 * inside workshop_sessions.context_json. They support filtered
 * queries that would otherwise require JSON path expressions.</p>
 */
public interface WorkshopAttributeRepository
        extends JpaRepository<WorkshopAttribute, UUID> {

    /**
     * Return all attributes for a session, ordered by importance rank.
     *
     * @param sessionId owning session UUID
     * @return attributes ordered by importance then name
     */
    List<WorkshopAttribute> findBySessionIdOrderByImportanceAscNameAsc(
            UUID sessionId);

    /**
     * Return attributes filtered by confidence level.
     *
     * @param sessionId  owning session UUID
     * @param confidence one of: confirmed | inferred | tentative
     * @return filtered attributes ordered by importance
     */
    List<WorkshopAttribute> findBySessionIdAndConfidenceOrderByImportanceAsc(
            UUID sessionId, String confidence);

    /**
     * Find an attribute by its stable agent-assigned ID within a session.
     *
     * @param sessionId   owning session UUID
     * @param attributeId agent-assigned ID (e.g. QA-001)
     * @return Optional attribute record
     */
    Optional<WorkshopAttribute> findBySessionIdAndAttributeId(
            UUID sessionId, String attributeId);

    /**
     * Delete all attributes for a session before replacing them.
     * Called when context_json is updated with a full attribute replacement.
     *
     * @param sessionId owning session UUID
     */
    void deleteBySessionId(UUID sessionId);
}
