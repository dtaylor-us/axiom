package com.memoria.api.domain.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "distillation_jobs")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DistillationJob {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private DistillationJobStatus status;

    @Column(nullable = false)
    private Integer sessionCount;

    @Column(nullable = false)
    private Integer totalCandidates;

    @Column(nullable = false)
    private Integer totalPersisted;

    @Column(nullable = false)
    private Integer totalSuperseded;

    @Column(nullable = false)
    private Integer totalConflicts;

    // Per-session results stored as JSONB.
    // Schema: list of { sessionId, pillar, status, candidates,
    //                   persisted, superseded, conflicts, error }
    @Column(columnDefinition = "jsonb")
    private String sessionResults;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    private LocalDateTime completedAt;
}
