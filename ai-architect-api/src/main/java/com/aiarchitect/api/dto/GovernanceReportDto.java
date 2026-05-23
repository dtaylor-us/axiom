package com.aiarchitect.api.dto;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;
import java.util.List;
import java.util.Map;
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
    private int characteristicAlignment;
    private int tradeOffQuality;
    private int adlEnforceability;
    private int riskAwareness;
    private int consistencyBonus;
    private Map<String, String> scoreEvidence;
    private int architecturalSoundness;
    private int riskMitigation;
    private int governanceCompleteness;
    private String justification;
    private boolean shouldReiterate;
    private Object reviewFindings;
    private List<Object> improvementRecommendations;
    private Instant createdAt;
}
