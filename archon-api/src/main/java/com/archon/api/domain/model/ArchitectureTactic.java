package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/**
 * Persists a single architecture tactic recommendation for a conversation.
 *
 * <p>Tactic catalog source: Bass, Clements, Kazman
 * "Software Architecture in Practice", 4th ed., SEI/Addison-Wesley 2021.
 *
 * <p>Populated by the Python agent's TacticsAdvisorTool (pipeline stage 4b)
 * via {@link com.archon.api.service.TacticsService#saveTactics}.
 */
@Entity
@Table(name = "architecture_tactics")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class ArchitectureTactic {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    @Column(name = "tactic_id", nullable = false)
    private String tacticId;

    @Column(name = "tactic_name", nullable = false)
    private String tacticName;

    @Column(name = "characteristic_name", nullable = false)
    private String characteristicName;

    @Column(nullable = false)
    private String category;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String description;

    @Column(name = "concrete_application", nullable = false, columnDefinition = "TEXT")
    private String concreteApplication;

    /**
     * Ordered list of tooling or pattern names that implement this tactic.
     * Stored as a JSONB array in PostgreSQL.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "implementation_examples", columnDefinition = "jsonb", nullable = false)
    private String implementationExamples;

    @Column(name = "already_addressed", nullable = false)
    @Builder.Default
    private boolean alreadyAddressed = false;

    @Column(name = "address_evidence", nullable = false)
    @Builder.Default
    private String addressEvidence = "";

    /** Design effort required: low | medium | high */
    @Column(nullable = false)
    private String effort;

    /** Recommendation priority: critical | recommended | optional */
    @Column(nullable = false)
    private String priority;

    @CreationTimestamp
    private Instant createdAt;
}
