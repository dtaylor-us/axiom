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
    public Project createProject(String name, String description) {
        LocalDateTime now = LocalDateTime.now();
        Project project = Project.builder()
                .name(name)
                .description(description)
                .status(ProjectStatus.ACTIVE)
                .createdAt(now)
                .updatedAt(now)
                .build();
        return projectRepository.save(project);
    }

    @Transactional(readOnly = true)
    public Project getProject(UUID id) {
        return projectRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));
    }

    @Transactional(readOnly = true)
    public List<Project> listProjects() {
        return projectRepository.findByStatusOrderByCreatedAtDesc(ProjectStatus.ACTIVE);
    }

    @Transactional
    public Project updateProject(UUID id, String name, String description) {
        Project project = getProject(id);
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
    public Project archiveProject(UUID id) {
        Project project = getProject(id);
        project.setStatus(ProjectStatus.ARCHIVED);
        project.setUpdatedAt(LocalDateTime.now());
        return projectRepository.save(project);
    }
}
