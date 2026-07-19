package com.memoria.api.controller;

import com.memoria.api.domain.model.Pillar;
import com.memoria.api.dto.DistillSessionRequest;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.service.AuthenticationUserResolver;
import com.memoria.api.service.DistillationService;
import com.memoria.api.service.ProjectService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria")
@RequiredArgsConstructor
public class DistillationController {

    private final DistillationService distillationService;
    private final ProjectService projectService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping("/distill-session")
    @ResponseStatus(HttpStatus.CREATED)
    public DistillSessionResponse distillSession(
            @Valid @RequestBody DistillSessionRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(request.projectId(), userIdHeader, authentication);
        return distillationService.distillLinkedSession(request);
    }

    @PostMapping("/sessions/{pillar}/{sessionId}/distill")
    @ResponseStatus(HttpStatus.CREATED)
    public DistillSessionResponse distillLinkedSession(
            @PathVariable Pillar pillar,
            @PathVariable UUID sessionId,
            @RequestBody DistillSessionRequest request,
            @RequestHeader(value = "X-Axiom-User-Id", required = false) String userIdHeader,
            Authentication authentication) {
        validateProjectAccess(request.projectId(), userIdHeader, authentication);
        DistillSessionRequest normalized = new DistillSessionRequest(
                request.projectId(),
                pillar,
                sessionId,
                request.sessionSummary(),
                request.sessionPayload());
        return distillationService.distillLinkedSession(normalized);
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
