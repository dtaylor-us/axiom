package com.lens.api.domain.model;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "review_reports")
public class ReviewReport {

    @Id
    @Column(name = "id", nullable = false)
    private UUID id;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(name = "executive_summary")
    private String executiveSummary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "azure_waf_scorecard", columnDefinition = "jsonb")
    private JsonNode azureWafScorecard;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "atam_analysis", columnDefinition = "jsonb")
    private JsonNode atamAnalysis;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "sei_analysis", columnDefinition = "jsonb")
    private JsonNode seiAnalysis;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "structural_analysis", columnDefinition = "jsonb")
    private JsonNode structuralAnalysis;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "insufficient_info_gaps", columnDefinition = "jsonb")
    private JsonNode insufficientInfoGaps;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "recommendation_roadmap", columnDefinition = "jsonb")
    private JsonNode recommendationRoadmap;

    @Enumerated(EnumType.STRING)
    @Column(name = "overall_rating", length = 50)
    private OverallRating overallRating;

    @Column(name = "generated_at", nullable = false)
    private LocalDateTime generatedAt;

    @Transient
    private List<ReviewFinding> findings = new ArrayList<>();

    @Transient
    private List<ReviewRisk> risks = new ArrayList<>();

    public ReviewReport() {
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public UUID getSessionId() {
        return sessionId;
    }

    public void setSessionId(UUID sessionId) {
        this.sessionId = sessionId;
    }

    public String getExecutiveSummary() {
        return executiveSummary;
    }

    public void setExecutiveSummary(String executiveSummary) {
        this.executiveSummary = executiveSummary;
    }

    public JsonNode getAzureWafScorecard() {
        return azureWafScorecard;
    }

    public void setAzureWafScorecard(JsonNode azureWafScorecard) {
        this.azureWafScorecard = azureWafScorecard;
    }

    public JsonNode getAtamAnalysis() {
        return atamAnalysis;
    }

    public void setAtamAnalysis(JsonNode atamAnalysis) {
        this.atamAnalysis = atamAnalysis;
    }

    public JsonNode getSeiAnalysis() {
        return seiAnalysis;
    }

    public void setSeiAnalysis(JsonNode seiAnalysis) {
        this.seiAnalysis = seiAnalysis;
    }

    public JsonNode getStructuralAnalysis() {
        return structuralAnalysis;
    }

    public void setStructuralAnalysis(JsonNode structuralAnalysis) {
        this.structuralAnalysis = structuralAnalysis;
    }

    public JsonNode getInsufficientInfoGaps() {
        return insufficientInfoGaps;
    }

    public void setInsufficientInfoGaps(JsonNode insufficientInfoGaps) {
        this.insufficientInfoGaps = insufficientInfoGaps;
    }

    public JsonNode getRecommendationRoadmap() {
        return recommendationRoadmap;
    }

    public void setRecommendationRoadmap(JsonNode recommendationRoadmap) {
        this.recommendationRoadmap = recommendationRoadmap;
    }

    public OverallRating getOverallRating() {
        return overallRating;
    }

    public void setOverallRating(OverallRating overallRating) {
        this.overallRating = overallRating;
    }

    public LocalDateTime getGeneratedAt() {
        return generatedAt;
    }

    public void setGeneratedAt(LocalDateTime generatedAt) {
        this.generatedAt = generatedAt;
    }

    public List<ReviewFinding> getFindings() {
        return findings;
    }

    public void setFindings(List<ReviewFinding> findings) {
        this.findings = findings;
    }

    public List<ReviewRisk> getRisks() {
        return risks;
    }

    public void setRisks(List<ReviewRisk> risks) {
        this.risks = risks;
    }
}
