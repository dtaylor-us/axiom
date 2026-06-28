package com.lens.api.repository;

import com.lens.api.domain.model.ReviewSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ReviewSessionRepository extends JpaRepository<ReviewSession, UUID> {

    List<ReviewSession> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<ReviewSession> findByIdAndUserId(UUID id, UUID userId);
}
