package com.memoria.api.service;

import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectStatus;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ProjectServiceTest {

    private ProjectRepository projectRepository;
    private ProjectService projectService;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        projectService = new ProjectService(projectRepository);
    }

    @Test
    void createProject_setsStatusToActive() {
        when(projectRepository.save(any(Project.class))).thenAnswer(invocation -> invocation.getArgument(0));

        Project project = projectService.createProject("Axiom", "Memory");

        assertThat(project.getStatus()).isEqualTo(ProjectStatus.ACTIVE);
    }

    @Test
    void createProject_setsTimestamps() {
        when(projectRepository.save(any(Project.class))).thenAnswer(invocation -> invocation.getArgument(0));

        Project project = projectService.createProject("Axiom", null);

        assertThat(project.getCreatedAt()).isNotNull();
        assertThat(project.getUpdatedAt()).isNotNull();
    }

    @Test
    void getProject_throwsNotFound_whenMissing() {
        UUID projectId = UUID.randomUUID();
        when(projectRepository.findById(projectId)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> projectService.getProject(projectId))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessage("Project not found");
    }

    @Test
    void listProjects_returnsOnlyActive() {
        Project project = Project.builder().status(ProjectStatus.ACTIVE).createdAt(LocalDateTime.now()).build();
        when(projectRepository.findByStatusOrderByCreatedAtDesc(ProjectStatus.ACTIVE)).thenReturn(List.of(project));

        List<Project> projects = projectService.listProjects();

        assertThat(projects).containsExactly(project);
    }

    @Test
    void archiveProject_setsStatusArchived() {
        UUID projectId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).status(ProjectStatus.ACTIVE).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(projectRepository.save(any(Project.class))).thenAnswer(invocation -> invocation.getArgument(0));

        Project archived = projectService.archiveProject(projectId);

        assertThat(archived.getStatus()).isEqualTo(ProjectStatus.ARCHIVED);
    }
}
