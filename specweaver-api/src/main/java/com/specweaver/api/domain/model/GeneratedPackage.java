package com.specweaver.api.domain.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * ArchInputPackage generated from extracted SpecWeaver documents.
 *
 * @author OpenAI
 */
@Entity
@Table(name = "generated_packages")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class GeneratedPackage {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "session_id", nullable = false)
    private Session session;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "package_json", columnDefinition = "jsonb", nullable = false)
    private String packageJson;

    @Column(name = "total_requirements")
    private int totalRequirements;

    @Column(name = "high_confidence_count")
    private int highConfidenceCount;

    @Column(name = "inferred_count")
    private int inferredCount;

    @Column(name = "duplicate_count")
    private int duplicateCount;

    @Column(name = "gap_count")
    private int gapCount;

    @Column(name = "conflict_count")
    private int conflictCount;

    @Column(name = "readiness_score")
    @Builder.Default
    private BigDecimal readinessScore = BigDecimal.ZERO;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @Column(name = "sent_to_archon_at")
    private Instant sentToArchonAt;

    @Column(name = "archon_conversation_id")
    private UUID archonConversationId;

    @Column(name = "brief_text")
    private String briefText;
}
