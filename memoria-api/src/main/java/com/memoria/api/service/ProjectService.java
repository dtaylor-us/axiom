package com.memoria.api.service;

import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectStatus;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class ProjectService {

    private final ProjectRepository projectRepository;

    @Transactional
    public Project createProject(UUID userId, String name, String description) {
        LocalDateTime now = LocalDateTime.now();
        Project project = Project.builder()
                .userId(userId)
                .name(name)
                .description(description)
                .status(ProjectStatus.ACTIVE)
                .createdAt(now)
                .updatedAt(now)
                .build();
        return projectRepository.save(project);
    }

    @Transactional(readOnly = true)
    public Project getProject(UUID id, UUID userId) {
        return projectRepository.findById(id)
                .filter(project -> project.getUserId().equals(userId))
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));
    }

    @Transactional(readOnly = true)
    public List<Project> listProjects(UUID userId) {
        return projectRepository.findByUserIdAndStatusOrderByUpdatedAtDesc(userId, ProjectStatus.ACTIVE);
    }

    @Transactional
    public Project updateProject(UUID id, UUID userId, String name, String description) {
        Project project = getProject(id, userId);
        if (name != null) {
            project.setName(name);
        }
        if (description != null) {
            project.setDescription(description);
        }
        project.setUpdatedAt(LocalDateTime.now());
        return projectRepository.save(project);
    }

    @Transactional
    public Project archiveProject(UUID id, UUID userId) {
        Project project = getProject(id, userId);
        project.setStatus(ProjectStatus.ARCHIVED);
        project.setUpdatedAt(LocalDateTime.now());
        return projectRepository.save(project);
    }
}
