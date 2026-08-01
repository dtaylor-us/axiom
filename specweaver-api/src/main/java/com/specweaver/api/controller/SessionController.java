package com.specweaver.api.controller;

import com.specweaver.api.dto.request.CreateSessionRequest;
import com.specweaver.api.dto.request.UpdateSessionRequest;
import com.specweaver.api.dto.response.SessionResponse;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.SessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/**
 * REST endpoints for SpecWeaver session lifecycle operations.
 *
 * @author OpenAI
 */
@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SessionResponse createSession(
            @Valid @RequestBody(required = false) CreateSessionRequest request,
            Authentication authentication) {
        return sessionService.createSession(request, userResolver.resolveUserId(authentication));
    }

    @GetMapping
    public List<SessionResponse> listSessions(Authentication authentication) {
        return sessionService.listSessions(userResolver.resolveUserId(authentication));
    }

    @GetMapping("/{sessionId}")
    public SessionResponse getSession(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        return sessionService.getSession(sessionId, userResolver.resolveUserId(authentication));
    }

    @PatchMapping("/{sessionId}")
    public SessionResponse updateSession(
            @PathVariable UUID sessionId,
            @Valid @RequestBody UpdateSessionRequest request,
            Authentication authentication) {
        return sessionService.updateSessionTitle(sessionId, userResolver.resolveUserId(authentication), request);
    }

    @DeleteMapping("/{sessionId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteSession(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        sessionService.deleteSession(sessionId, userResolver.resolveUserId(authentication));
    }
}
