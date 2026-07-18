package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/**
 * Append-only persisted event emitted during a pipeline run.
 *
 * <p>Used to replay SSE events to reconnecting clients.</p>
 */
@Entity
@Table(name = "pipeline_events")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PipelineEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "run_id", nullable = false)
    private PipelineRun run;

    private Integer sequenceNum;
    private String eventType;
    private String stageName;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String payload;

    @Builder.Default
    private Instant emittedAt = Instant.now();
}

