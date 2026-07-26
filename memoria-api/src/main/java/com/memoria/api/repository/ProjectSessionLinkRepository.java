package com.memoria.api.repository;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.ProjectSessionLink;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ProjectSessionLinkRepository extends JpaRepository<ProjectSessionLink, UUID> {
    List<ProjectSessionLink> findByProjectId(UUID projectId);
    Optional<ProjectSessionLink> findByPillarAndSessionId(Pillar pillar, UUID sessionId);
}
