package com.lens.api.service;

import com.lens.api.domain.model.ReviewReport;

import java.util.UUID;

public class ReviewPipelineService {

    private final ReviewReportService reviewReportService;

    public ReviewPipelineService(ReviewReportService reviewReportService) {
        this.reviewReportService = reviewReportService;
    }

    public ReviewReport runReview(UUID sessionId) {
        return reviewReportService.createEmptyReport(sessionId);
    }
}
