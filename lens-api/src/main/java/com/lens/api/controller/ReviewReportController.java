package com.lens.api.controller;

import com.lens.api.domain.model.ReviewReport;
import com.lens.api.service.ReviewPipelineService;
import com.lens.api.service.ReviewReportService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions/{sessionId}")
public class ReviewReportController {

    private final ReviewPipelineService reviewPipelineService = new ReviewPipelineService(new ReviewReportService());

    @PostMapping("/review")
    public ReviewReport review(@PathVariable UUID sessionId) {
        return reviewPipelineService.runReview(sessionId);
    }

    @GetMapping("/report")
    @ResponseStatus(HttpStatus.OK)
    public ReviewReport report(@PathVariable UUID sessionId) {
        return reviewPipelineService.runReview(sessionId);
    }
}
