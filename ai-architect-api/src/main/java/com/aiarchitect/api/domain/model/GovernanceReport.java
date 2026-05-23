package com.aiarchitect.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "governance_reports")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class GovernanceReport {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    @Column(nullable = false)
    @Builder.Default
    private int iteration = 0;

    @Column(name = "governance_score")
    private Integer governanceScore;

    @Column(name = "review_completed_fully")
    @Builder.Default
    private boolean reviewCompletedFully = false;

    @Column(name = "governance_score_confidence")
    @Builder.Default
    private String governanceScoreConfidence = "unavailable";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "failed_review_nodes", columnDefinition = "jsonb")
    private String failedReviewNodes;

    @Column(name = "requirement_coverage", nullable = false)
    @Builder.Default
    private int requirementCoverage = 0;

    @Column(name = "architectural_soundness", nullable = false)
    @Builder.Default
    private int architecturalSoundness = 0;

    @Column(name = "risk_mitigation", nullable = false)
    @Builder.Default
    private int riskMitigation = 0;

    @Column(name = "governance_completeness", nullable = false)
    @Builder.Default
    private int governanceCompleteness = 0;

    @Column(columnDefinition = "TEXT")
    private String justification;

    @Column(name = "should_reiterate", nullable = false)
    @Builder.Default
    private boolean shouldReiterate = false;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "review_findings", columnDefinition = "jsonb")
    private String reviewFindings;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "improvement_recommendations", columnDefinition = "jsonb")
    private String improvementRecommendations;

    @CreationTimestamp
    private Instant createdAt;
}
