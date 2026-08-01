package com.memoria.api.repository;

import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ProjectRepository extends JpaRepository<Project, UUID> {
    List<Project> findByStatusOrderByCreatedAtDesc(ProjectStatus status);

    List<Project> findByUserIdAndStatusOrderByUpdatedAtDesc(UUID userId, ProjectStatus status);
}
