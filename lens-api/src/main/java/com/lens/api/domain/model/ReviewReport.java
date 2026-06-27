package com.lens.api.domain.model;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public record ReviewReport(
    UUID id,
    UUID sessionId,
    String executiveSummary,
    JsonNode azureWafScorecard,
    JsonNode atamAnalysis,
    JsonNode seiAnalysis,
    JsonNode structuralAnalysis,
    JsonNode insufficientInfoGaps,
    List<ReviewFinding> findings,
    List<ReviewRisk> risks,
    String recommendationRoadmap,
    OverallRating overallRating,
    LocalDateTime generatedAt
) {}
