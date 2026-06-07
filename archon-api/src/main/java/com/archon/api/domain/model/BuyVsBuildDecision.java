package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/**
 * Entity representing a single buy-vs-build decision for an architecture component.
 *
 * <p>Persisted from the Python agent stage {@code buy_vs_build_analysis} (stage 6b).
 * Stores a sourcing recommendation (build | buy | adopt), rationale, alternatives
 * considered, and conflict metadata when user preferences disagree with best practice.
 */
@Entity
@Table(name = "buy_vs_build_decisions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class BuyVsBuildDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    @Column(name = "component_name", nullable = false)
    private String componentName;

    @Column(nullable = false)
    private String recommendation;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String rationale;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "alternatives_considered", columnDefinition = "jsonb")
    private String alternativesConsidered;

    @Column(name = "recommended_solution")
    private String recommendedSolution;

    @Column(name = "estimated_build_cost")
    private String estimatedBuildCost;

    @Column(name = "vendor_lock_in_risk", nullable = false)
    private String vendorLockInRisk;

    @Column(name = "integration_effort", nullable = false)
    private String integrationEffort;

    @Column(name = "conflicts_with_user_preference", nullable = false)
    @Builder.Default
    private boolean conflictsWithUserPreference = false;

    @Column(name = "conflict_explanation", columnDefinition = "TEXT")
    private String conflictExplanation;

    @Column(name = "is_core_differentiator", nullable = false)
    @Builder.Default
    private boolean isCoreDifferentiator = false;

    @CreationTimestamp
    private Instant createdAt;
}

