package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcType;
import org.hibernate.dialect.PostgreSQLEnumJdbcType;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Durable record of one pipeline execution.
 *
 * <p>A pipeline run is created before the agent stream begins. The SSE stream is a view
 * over this run record and its event log.</p>
 */
@Entity
@Table(name = "pipeline_runs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PipelineRun {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id", nullable = false)
    private Conversation conversation;

    private Integer iteration;

    @Enumerated(EnumType.STRING)
    @Column(columnDefinition = "pipeline_run_status")
    @JdbcType(PostgreSQLEnumJdbcType.class)
    private PipelineRunStatus status;

    private Instant startedAt;
    private Instant completedAt;
    private String lastStageCompleted;
    private Integer governanceScore;
    private String governanceConfidence;
    @Builder.Default
    private Boolean hasGaps = false;
    private String gapSummary;
    private String errorStage;
    private String errorMessage;
    private Integer totalTokens;

    @Column(precision = 10, scale = 4)
    private BigDecimal estimatedCostUsd;

    @OneToMany(mappedBy = "run", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    @OrderBy("sequenceNum ASC")
    @Builder.Default
    private List<PipelineEvent> events = new ArrayList<>();

    @PrePersist
    void prePersist() {
        if (startedAt == null) {
            startedAt = Instant.now();
        }
    }
}

