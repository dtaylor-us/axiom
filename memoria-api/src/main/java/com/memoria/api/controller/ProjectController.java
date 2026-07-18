package com.memoria.api.controller;

import com.memoria.api.dto.CreateProjectRequest;
import com.memoria.api.dto.ProjectResponse;
import com.memoria.api.dto.UpdateProjectRequest;
import com.memoria.api.service.AuthenticationUserResolver;
import com.memoria.api.service.ProjectService;
import com.memoria.api.service.ResponseMapper;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects")
@RequiredArgsConstructor
public class ProjectController {

    private final ProjectService projectService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ProjectResponse createProject(
            @Valid @RequestBody CreateProjectRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        resolveUser(userIdHeader, authentication);
        return ResponseMapper.toProjectResponse(projectService.createProject(request.name(), request.description()));
    }

    @GetMapping
    public List<ProjectResponse> listProjects(
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        resolveUser(userIdHeader, authentication);
        return projectService.listProjects().stream()
                .map(ResponseMapper::toProjectResponse)
                .toList();
    }

    @GetMapping("/{id}")
    public ProjectResponse getProject(
            @PathVariable UUID id,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        resolveUser(userIdHeader, authentication);
        return ResponseMapper.toProjectResponse(projectService.getProject(id));
    }

    @PutMapping("/{id}")
    public ProjectResponse updateProject(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateProjectRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        resolveUser(userIdHeader, authentication);
        return ResponseMapper.toProjectResponse(projectService.updateProject(id, request.name(), request.description()));
    }

    @DeleteMapping("/{id}")
    public ProjectResponse archiveProject(
            @PathVariable UUID id,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        resolveUser(userIdHeader, authentication);
        return ResponseMapper.toProjectResponse(projectService.archiveProject(id));
    }

    private UUID resolveUser(String userIdHeader, Authentication authentication) {
        if (userIdHeader != null && !userIdHeader.isBlank()) {
            return UUID.fromString(userIdHeader);
        }
        return userResolver.resolveUserId(authentication);
    }
}
