package com.aiarchitect.api.workshop.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Denormalised record for one quality attribute derived during a workshop.
 *
 * <p>The authoritative state is in
 * {@link WorkshopSession#getContextJson()}. This entity provides
 * queryable access so callers can filter attributes by confidence,
 * category, or importance without parsing JSON in application code.</p>
 *
 * <p>Records are written and updated in sync with context_json by
 * {@link com.aiarchitect.api.workshop.service.WorkshopService}
 * after each turn.</p>
 */
@Entity
@Table(name = "workshop_attributes")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class WorkshopAttribute {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @EqualsAndHashCode.Include
    private UUID id;

    /** Owning session. */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "session_id", nullable = false)
    private WorkshopSession session;

    /** Stable attribute identifier from the Python agent (e.g. QA-001). */
    @Column(nullable = false)
    private String attributeId;

    /** Canonical quality attribute name (e.g. Availability, Performance). */
    @Column(nullable = false)
    private String name;

    /**
     * Quality attribute category.
     * One of: availability, performance, security, modifiability, scalability,
     * testability, deployability, usability, interoperability, data_integrity,
     * auditability, recoverability, cost, other.
     */
    @Column(nullable = false)
    private String category;

    /** Stakeholder-assessed importance: critical | high | medium | low. */
    @Column(nullable = false)
    private String importance;

    /**
     * Evidence quality: confirmed | inferred | tentative.
     * Confirmed means the user explicitly stated this attribute matters.
     * Inferred means strong contextual evidence exists.
     * Tentative means possible but unvalidated.
     */
    @Column(nullable = false)
    private String confidence;

    /** System-specific description of what this attribute means. */
    @Column
    private String description;

    /**
     * The primary QA scenario in JSON format (six-part structure from
     * Bass, Clements, Kazman "Software Architecture in Practice" 4th ed.).
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String scenarioJson;

    /**
     * Verbatim phrases from user input supporting this attribute.
     * Stored as a JSON array of strings.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    @Builder.Default
    private String evidenceQuotes = "[]";

    /**
     * Open questions needed to fully ground this attribute.
     * Stored as a JSON array of strings.
     */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    @Builder.Default
    private String openQuestions = "[]";

    /** Conversation turn in which this attribute was first derived. */
    @Column
    private Integer derivedInTurn;

    /** First user-triggered generation pass that created this row. */
    @Column
    private Integer firstGenerationPass;

    /** Most recent generation pass that updated this row. */
    @Column
    private Integer lastGenerationPass;

    @CreationTimestamp
    @Column(nullable = false)
    private Instant createdAt;
}
