package com.specweaver.api.repository;

import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.SessionDocument;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for documents attached to SpecWeaver sessions.
 */
public interface SessionDocumentRepository extends JpaRepository<SessionDocument, UUID> {

    List<SessionDocument> findBySessionIdOrderByCreatedAtAsc(UUID sessionId);

    List<SessionDocument> findBySessionIdAndStatusOrderByCreatedAtAsc(UUID sessionId, DocumentStatus status);

    Optional<SessionDocument> findByIdAndSessionId(UUID id, UUID sessionId);
}
