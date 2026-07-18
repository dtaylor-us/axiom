package com.memoria.api.controller;

import com.memoria.api.dto.CreateSessionLinkRequest;
import com.memoria.api.dto.SessionLinkResponse;
import com.memoria.api.service.ResponseMapper;
import com.memoria.api.service.SessionLinkService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects/{projectId}/sessions")
@RequiredArgsConstructor
public class SessionLinkController {

    private final SessionLinkService sessionLinkService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SessionLinkResponse linkSession(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateSessionLinkRequest request) {
        return ResponseMapper.toSessionLinkResponse(
                sessionLinkService.linkSession(projectId, request.pillar(), request.sessionId()));
    }

    @GetMapping
    public List<SessionLinkResponse> listLinks(@PathVariable UUID projectId) {
        return sessionLinkService.listLinks(projectId).stream()
                .map(ResponseMapper::toSessionLinkResponse)
                .toList();
    }

    @DeleteMapping("/{linkId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void removeLink(@PathVariable UUID projectId, @PathVariable UUID linkId) {
        sessionLinkService.removeLink(projectId, linkId);
    }
}
