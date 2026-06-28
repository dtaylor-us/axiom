package com.lens.api.controller;

import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.service.AuthenticationUserResolver;
import com.lens.api.service.EvidenceIngestionService;
import com.lens.api.service.ReviewSessionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions/{sessionId}/evidence")
@RequiredArgsConstructor
public class EvidenceController {

    private final EvidenceIngestionService evidenceIngestionService;
    private final ReviewSessionService reviewSessionService;
    private final AuthenticationUserResolver userResolver;

    public record SubmitEvidenceRequest(@NotBlank String evidenceType, @NotBlank String content, String sourceLabel) {}

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ArchitectureEvidence submitEvidence(
            @PathVariable UUID sessionId,
            @Valid @RequestBody SubmitEvidenceRequest request,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return evidenceIngestionService.submitEvidence(
                sessionId,
                userId,
                request.evidenceType(),
                request.content(),
                request.sourceLabel());
    }

    @GetMapping
    public List<ArchitectureEvidence> listEvidence(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        reviewSessionService.getSession(sessionId, userId);
        return evidenceIngestionService.listEvidence(sessionId);
    }

    @DeleteMapping("/{evidenceId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteEvidence(
            @PathVariable UUID sessionId,
            @PathVariable UUID evidenceId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        reviewSessionService.getSession(sessionId, userId);
        evidenceIngestionService.deleteEvidence(sessionId, evidenceId);
    }
}
