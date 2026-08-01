package com.lens.api.controller;

import com.lens.api.domain.model.GapQuestion;
import com.lens.api.service.AuthenticationUserResolver;
import com.lens.api.service.GapElicitationService;
import com.lens.api.service.ReviewSessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions/{sessionId}")
@RequiredArgsConstructor
public class GapController {

    private final GapElicitationService gapElicitationService;
    private final ReviewSessionService reviewSessionService;
    private final AuthenticationUserResolver userResolver;

    public record AnswerGapQuestionRequest(String answer, boolean skipped) {}

    @PostMapping("/gaps/generate")
    public List<GapQuestion> generate(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return gapElicitationService.generateNextRound(sessionId, userId);
    }

    @PostMapping("/gaps/{questionId}/answer")
    public GapQuestion answer(
            @PathVariable UUID sessionId,
            @PathVariable UUID questionId,
            @Valid @RequestBody AnswerGapQuestionRequest request,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return gapElicitationService.answerQuestion(
                sessionId,
                questionId,
                request.answer(),
                request.skipped(),
                userId);
    }

    @GetMapping("/gaps")
    public List<GapQuestion> list(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return gapElicitationService.getQuestionsForCurrentRound(sessionId, userId);
    }

    @PostMapping("/gaps/assess")
    public Map<String, Object> assess(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return gapElicitationService.assessGaps(sessionId, userId);
    }

    @PostMapping("/proceed")
    @ResponseStatus(HttpStatus.OK)
    public Map<String, Object> proceed(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        List<String> insufficient = reviewSessionService.forceProceed(sessionId, userId);
        return Map.of(
                "status", "READY_FOR_REVIEW",
                "insufficientInfoGaps", insufficient);
    }
}
