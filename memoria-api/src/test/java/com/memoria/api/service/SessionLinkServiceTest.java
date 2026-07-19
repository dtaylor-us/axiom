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
import java.nio.charset.StandardCharsets;
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
    void linkSession_returnsExistingLink_whenAlreadyLinkedToRequestedProject() {
        UUID projectId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).name("Current project").build();
        ProjectSessionLink existingLink = ProjectSessionLink.builder()
                .id(UUID.randomUUID())
                .project(project)
                .pillar(Pillar.LENS)
                .sessionId(sessionId)
                .build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(linkRepository.findByPillarAndSessionId(Pillar.LENS, sessionId))
                .thenReturn(Optional.of(existingLink));

        assertThat(sessionLinkService.linkSession(projectId, Pillar.LENS, sessionId)).isSameAs(existingLink);
        verify(linkRepository, never()).save(any(ProjectSessionLink.class));
    }

    @Test
    void linkSession_identifiesProject_whenAlreadyLinkedElsewhere() {
        UUID projectId = UUID.randomUUID();
        UUID otherProjectId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        when(projectRepository.findById(projectId))
                .thenReturn(Optional.of(Project.builder().id(projectId).name("Current project").userId(UUID.randomUUID()).build()));
        when(linkRepository.findByPillarAndSessionId(Pillar.LENS, sessionId))
                .thenReturn(Optional.of(ProjectSessionLink.builder()
                        .project(Project.builder().id(otherProjectId).name("Other project").userId(UUID.randomUUID()).build())
                        .build()));

        assertThatThrownBy(() -> sessionLinkService.linkSession(projectId, Pillar.LENS, sessionId))
                .isInstanceOf(DuplicateSessionLinkException.class)
                .hasMessage("Session is already linked to project 'Other project' (" + otherProjectId + ")")
                .satisfies(error -> {
                    DuplicateSessionLinkException duplicate = (DuplicateSessionLinkException) error;
                    assertThat(duplicate.getProjectId()).isEqualTo(otherProjectId);
                    assertThat(duplicate.getProjectName()).isEqualTo("Other project");
                });
        verify(linkRepository, never()).save(any(ProjectSessionLink.class));
    }

    @Test
    void linkSession_claimsLinkFromLegacyLocalDevProject() {
        UUID projectId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Project project = Project.builder().id(projectId).name("Neteru Path").userId(UUID.randomUUID()).build();
        ProjectSessionLink legacyLink = ProjectSessionLink.builder()
                .id(UUID.randomUUID())
                .project(Project.builder()
                        .id(UUID.randomUUID())
                        .name("Neteru Path")
                        .userId(UUID.nameUUIDFromBytes("local-dev".getBytes(StandardCharsets.UTF_8)))
                        .build())
                .pillar(Pillar.ARCHON)
                .sessionId(sessionId)
                .build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(linkRepository.findByPillarAndSessionId(Pillar.ARCHON, sessionId)).thenReturn(Optional.of(legacyLink));
        when(linkRepository.save(legacyLink)).thenReturn(legacyLink);

        assertThat(sessionLinkService.linkSession(projectId, Pillar.ARCHON, sessionId)).isSameAs(legacyLink);
        assertThat(legacyLink.getProject()).isSameAs(project);
        verify(linkRepository).save(legacyLink);
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
