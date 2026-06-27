package com.lens.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.lens.api.domain.model.OverallRating;
import com.lens.api.domain.model.ReviewFinding;
import com.lens.api.domain.model.ReviewReport;
import com.lens.api.domain.model.ReviewRisk;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public class ReviewReportService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    public ReviewReport createEmptyReport(UUID sessionId) {
        ObjectNode empty = objectMapper.createObjectNode();
        return new ReviewReport(
            UUID.randomUUID(),
            sessionId,
            "Lens review pending.",
            empty,
            empty,
            empty,
            empty,
            empty,
            List.<ReviewFinding>of(),
            List.<ReviewRisk>of(),
            "",
            OverallRating.APPROVED_WITH_CONDITIONS,
            LocalDateTime.now()
        );
    }
}
