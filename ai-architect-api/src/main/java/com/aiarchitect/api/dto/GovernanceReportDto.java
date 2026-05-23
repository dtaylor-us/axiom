package com.aiarchitect.api.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Data
@Builder
public class GovernanceReportDto {
    private UUID id;
    private UUID conversationId;
    private int iteration;
    private Integer governanceScore;
    private String governanceScoreConfidence;
    private boolean reviewCompletedFully;
    private List<String> failedReviewNodes;
    private int requirementCoverage;
    private int architecturalSoundness;
    private int riskMitigation;
    private int governanceCompleteness;
    private String justification;
    private boolean shouldReiterate;
    private Object reviewFindings;
    private List<Object> improvementRecommendations;
    private Instant createdAt;
}
