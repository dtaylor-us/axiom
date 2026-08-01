package com.memoria.api.controller;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.dto.ProjectContextResponse;
import com.memoria.api.service.ProjectContextService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria")
@RequiredArgsConstructor
public class ProjectContextController {

    private final ProjectContextService projectContextService;

    @GetMapping("/projects/{projectId}/context")
    public ProjectContextResponse projectContext(@PathVariable UUID projectId) {
        return projectContextService.assembleProjectContext(projectId);
    }

    @GetMapping("/sessions/{pillar}/{sessionId}/context")
    public ProjectContextResponse sessionContext(
            @PathVariable Pillar pillar,
            @PathVariable UUID sessionId) {
        return projectContextService.assembleSessionContext(pillar, sessionId);
    }
}
