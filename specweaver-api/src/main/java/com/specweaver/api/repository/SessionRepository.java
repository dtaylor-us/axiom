package com.specweaver.api.repository;

import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for user-owned SpecWeaver sessions.
 */
public interface SessionRepository extends JpaRepository<Session, UUID> {

    List<Session> findByUserIdAndStatusNotOrderByCreatedAtDesc(UUID userId, SessionStatus status);

    Optional<Session> findByIdAndStatusNot(UUID id, SessionStatus status);
}
