package com.lens.api.repository;

import com.lens.api.domain.model.ArchitectureEvidence;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ArchitectureEvidenceRepository extends JpaRepository<ArchitectureEvidence, UUID> {

    List<ArchitectureEvidence> findBySessionIdOrderBySubmittedAtAsc(UUID sessionId);

    void deleteBySessionId(UUID sessionId);
}
