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
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(
        name = "architecture_decisions",
        uniqueConstraints = @UniqueConstraint(columnNames = {"project_id", "adr_number"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ArchitectureDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    @Column(name = "adr_number", nullable = false)
    private int adrNumber;

    @Column(name = "title", nullable = false, length = 500)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    @Builder.Default
    private AdrStatus status = AdrStatus.PROPOSED;

    @Column(name = "context", nullable = false, columnDefinition = "TEXT")
    private String context;

    @Column(name = "decision", nullable = false, columnDefinition = "TEXT")
    private String decision;

    @Column(name = "consequences", columnDefinition = "TEXT")
    private String consequences;

    @Column(name = "alternatives_considered", columnDefinition = "TEXT")
    private String alternativesConsidered;

    @Enumerated(EnumType.STRING)
    @Column(name = "source_pillar")
    private Pillar sourcePillar;

    @Column(name = "source_session_id")
    private UUID sourceSessionId;

    @Column(name = "source_memory_entry_id")
    private UUID sourceMemoryEntryId;

    @Column(name = "superseded_by_adr_number")
    private Integer supersededByAdrNumber;

    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();
}
