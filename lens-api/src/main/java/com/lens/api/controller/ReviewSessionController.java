package com.lens.api.controller;

import com.lens.api.domain.model.ReviewSession;
import com.lens.api.service.AuthenticationUserResolver;
import com.lens.api.service.ReviewSessionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.security.core.Authentication;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import lombok.RequiredArgsConstructor;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions")
@RequiredArgsConstructor
public class ReviewSessionController {

    private final ReviewSessionService reviewSessionService;
    private final AuthenticationUserResolver userResolver;

    public record CreateReviewSessionRequest(@NotBlank String title, String systemDescription) {}
    public record UpdateReviewSessionRequest(@NotBlank String title, String systemDescription) {}

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ReviewSession createSession(
            @Valid @RequestBody CreateReviewSessionRequest request,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewSessionService.createSession(userId, request.title(), request.systemDescription());
    }

    @GetMapping
    public List<ReviewSession> listSessions(
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewSessionService.listSessions(userId);
    }

    @GetMapping("/{id}")
    public ReviewSession getSession(
            @PathVariable UUID id,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewSessionService.getSession(id, userId);
    }

    @PutMapping("/{id}")
    public ReviewSession updateSession(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateReviewSessionRequest request,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewSessionService.updateSession(id, userId, request.title(), request.systemDescription());
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteSession(
            @PathVariable UUID id,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        reviewSessionService.deleteSession(id, userId);
    }
}
