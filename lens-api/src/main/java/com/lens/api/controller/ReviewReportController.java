package com.lens.api.controller;

import com.lens.api.domain.model.ReviewReport;
import com.lens.api.service.AuthenticationUserResolver;
import com.lens.api.service.ReviewPipelineService;
import com.lens.api.service.ReviewReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions/{sessionId}")
@RequiredArgsConstructor
public class ReviewReportController {

    private final ReviewPipelineService reviewPipelineService;
    private final ReviewReportService reviewReportService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping("/review")
    public ReviewReport review(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewPipelineService.startReview(sessionId, userId);
    }

    @GetMapping("/report")
    public ReviewReport report(
            @PathVariable UUID sessionId,
            Authentication authentication,
            @RequestHeader(name = "X-Axiom-User-Id", required = false) String userIdHeader) {
        String userId = userResolver.resolveUserId(authentication, userIdHeader).toString();
        return reviewReportService.getReport(sessionId, userId);
    }
}
