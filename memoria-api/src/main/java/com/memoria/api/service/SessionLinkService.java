package com.memoria.api.service;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.exception.DuplicateSessionLinkException;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class SessionLinkService {

    private static final UUID LEGACY_LOCAL_DEV_USER_ID =
            UUID.nameUUIDFromBytes("local-dev".getBytes(StandardCharsets.UTF_8));

    private final ProjectRepository projectRepository;
    private final ProjectSessionLinkRepository linkRepository;

    @Transactional
    public ProjectSessionLink linkSession(UUID projectId, Pillar pillar, UUID sessionId) {
        Project project = requireProject(projectId);
        ProjectSessionLink existingLink = linkRepository.findByPillarAndSessionId(pillar, sessionId)
                .orElse(null);
        if (existingLink != null) {
            if (existingLink.getProject().getId().equals(projectId)) {
                return existingLink;
            }
            if (existingLink.getProject().getUserId().equals(LEGACY_LOCAL_DEV_USER_ID)
                    && !project.getUserId().equals(LEGACY_LOCAL_DEV_USER_ID)) {
                log.info("Claiming legacy session link {} for project {}", existingLink.getId(), projectId);
                existingLink.setProject(project);
                return linkRepository.save(existingLink);
            }
            String projectName = existingLink.getProject().getName();
            throw new DuplicateSessionLinkException(
                    "Session is already linked to project '" + projectName + "' (" + existingLink.getProject().getId() + ")",
                    existingLink.getProject().getId(),
                    projectName);
        }
        ProjectSessionLink link = ProjectSessionLink.builder()
                .project(project)
                .pillar(pillar)
                .sessionId(sessionId)
                .linkedAt(LocalDateTime.now())
                .build();
        return linkRepository.save(link);
    }

    @Transactional(readOnly = true)
    public List<ProjectSessionLink> listLinks(UUID projectId) {
        requireProject(projectId);
        return linkRepository.findByProjectId(projectId);
    }

    @Transactional
    public void removeLink(UUID projectId, UUID linkId) {
        requireProject(projectId);
        ProjectSessionLink link = linkRepository.findById(linkId)
                .orElseThrow(() -> new ResourceNotFoundException("Session link not found"));
        if (!link.getProject().getId().equals(projectId)) {
            throw new ResourceNotFoundException("Session link not found");
        }
        linkRepository.delete(link);
    }

    private Project requireProject(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));
    }
}
