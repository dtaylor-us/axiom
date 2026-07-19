package com.memoria.api.controller;

import com.memoria.api.dto.CreateSessionLinkRequest;
import com.memoria.api.dto.SessionLinkResponse;
import com.memoria.api.service.AuthenticationUserResolver;
import com.memoria.api.service.ProjectService;
import com.memoria.api.service.ResponseMapper;
import com.memoria.api.service.SessionLinkService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects/{projectId}/sessions")
@RequiredArgsConstructor
public class SessionLinkController {

    private final SessionLinkService sessionLinkService;
    private final ProjectService projectService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SessionLinkResponse linkSession(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateSessionLinkRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return ResponseMapper.toSessionLinkResponse(
                sessionLinkService.linkSession(projectId, request.pillar(), request.sessionId()));
    }

    @GetMapping
    public List<SessionLinkResponse> listLinks(
            @PathVariable UUID projectId,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        return sessionLinkService.listLinks(projectId).stream()
                .map(ResponseMapper::toSessionLinkResponse)
                .toList();
    }

    @DeleteMapping("/{linkId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void removeLink(
            @PathVariable UUID projectId,
            @PathVariable UUID linkId,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(projectId, userIdHeader, authentication);
        sessionLinkService.removeLink(projectId, linkId);
    }

    private void validateProjectAccess(UUID projectId, String userIdHeader, Authentication authentication) {
        projectService.getProject(projectId, resolveUser(userIdHeader, authentication));
    }

    private UUID resolveUser(String userIdHeader, Authentication authentication) {
        if (userIdHeader != null && !userIdHeader.isBlank()) {
            try {
                return UUID.fromString(userIdHeader);
            } catch (IllegalArgumentException e) {
                return UUID.nameUUIDFromBytes(userIdHeader.getBytes(StandardCharsets.UTF_8));
            }
        }
        return userResolver.resolveUserId(authentication);
    }
}
