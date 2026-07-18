package com.memoria.api.service;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.exception.DuplicateSessionLinkException;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SessionLinkServiceTest {

    private ProjectRepository projectRepository;
    private ProjectSessionLinkRepository linkRepository;
    private SessionLinkService sessionLinkService;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        linkRepository = mock(ProjectSessionLinkRepository.class);
        sessionLinkService = new SessionLinkService(projectRepository, linkRepository);
    }

    @Test
    void linkSession_createsLink_withLinkedAt() {
        UUID projectId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(linkRepository.findByPillarAndSessionId(Pillar.ARCHON, sessionId)).thenReturn(Optional.empty());
        when(linkRepository.save(any(ProjectSessionLink.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ProjectSessionLink link = sessionLinkService.linkSession(projectId, Pillar.ARCHON, sessionId);

        assertThat(link.getProject()).isEqualTo(project);
        assertThat(link.getSessionId()).isEqualTo(sessionId);
        assertThat(link.getLinkedAt()).isNotNull();
    }

    @Test
    void linkSession_throwsDuplicate_whenAlreadyLinked() {
        UUID projectId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(Project.builder().id(projectId).build()));
        when(linkRepository.findByPillarAndSessionId(Pillar.LENS, sessionId))
                .thenReturn(Optional.of(ProjectSessionLink.builder().build()));

        assertThatThrownBy(() -> sessionLinkService.linkSession(projectId, Pillar.LENS, sessionId))
                .isInstanceOf(DuplicateSessionLinkException.class);
        verify(linkRepository, never()).save(any(ProjectSessionLink.class));
    }

    @Test
    void removeLink_throwsNotFound_whenLinkBelongsToDifferentProject() {
        UUID projectId = UUID.randomUUID();
        UUID otherProjectId = UUID.randomUUID();
        UUID linkId = UUID.randomUUID();
        ProjectSessionLink link = ProjectSessionLink.builder()
                .id(linkId)
                .project(Project.builder().id(otherProjectId).build())
                .build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(Project.builder().id(projectId).build()));
        when(linkRepository.findById(linkId)).thenReturn(Optional.of(link));

        assertThatThrownBy(() -> sessionLinkService.removeLink(projectId, linkId))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessage("Session link not found");
    }
}
