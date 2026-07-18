package com.memoria.api.service;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.dto.ProjectContextResponse;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ProjectContextServiceTest {

    private ProjectRepository projectRepository;
    private MemoryEntryRepository memoryEntryRepository;
    private ArchitectureDecisionRepository adrRepository;
    private ProjectSessionLinkRepository sessionLinkRepository;
    private ProjectContextService service;
    private UUID projectId;
    private Project project;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        memoryEntryRepository = mock(MemoryEntryRepository.class);
        adrRepository = mock(ArchitectureDecisionRepository.class);
        sessionLinkRepository = mock(ProjectSessionLinkRepository.class);
        service = new ProjectContextService(
                projectRepository,
                memoryEntryRepository,
                adrRepository,
                sessionLinkRepository);
        projectId = UUID.randomUUID();
        project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(adrRepository.findByProjectIdAndStatusInOrderByAdrNumberAsc(
                eq(projectId),
                eq(List.of(AdrStatus.ACCEPTED, AdrStatus.PROPOSED))))
                .thenReturn(List.of());
    }

    @Test
    void assembleProjectContext_includesOnlyActiveContextMemoryTypes() {
        MemoryEntry decision = entry(MemoryType.DECISION, MemoryStatus.ACTIVE);
        MemoryEntry requirement = entry(MemoryType.REQUIREMENT, MemoryStatus.ACTIVE);
        MemoryEntry constraint = entry(MemoryType.CONSTRAINT, MemoryStatus.ACTIVE);
        MemoryEntry risk = entry(MemoryType.RISK, MemoryStatus.ACTIVE);
        risk.setExpiresAt(LocalDateTime.now().plusDays(5));
        MemoryEntry qualityScore = entry(MemoryType.QUALITY_SCORE, MemoryStatus.ACTIVE);
        qualityScore.setExpiresAt(LocalDateTime.now().plusDays(5));
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId))
                .thenReturn(List.of(decision, requirement, constraint, risk, qualityScore));

        ProjectContextResponse response = service.assembleProjectContext(projectId);

        assertThat(response.decisions()).hasSize(1);
        assertThat(response.requirements()).hasSize(1);
        assertThat(response.constraints()).hasSize(1);
        assertThat(response.risks()).hasSize(1);
        assertThat(response.qualityScores()).hasSize(1);
    }

    @Test
    void assembleProjectContext_excludesLifecycleSessionSummaryAndExpiredEntries() {
        MemoryEntry active = entry(MemoryType.DECISION, MemoryStatus.ACTIVE);
        MemoryEntry stale = entry(MemoryType.DECISION, MemoryStatus.STALE);
        MemoryEntry superseded = entry(MemoryType.REQUIREMENT, MemoryStatus.SUPERSEDED);
        MemoryEntry archived = entry(MemoryType.CONSTRAINT, MemoryStatus.ARCHIVED);
        MemoryEntry sessionSummary = entry(MemoryType.SESSION_SUMMARY, MemoryStatus.ACTIVE);
        MemoryEntry expiredRisk = entry(MemoryType.RISK, MemoryStatus.ACTIVE);
        expiredRisk.setExpiresAt(LocalDateTime.now().minusDays(1));
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId))
                .thenReturn(List.of(active, stale, superseded, archived, sessionSummary, expiredRisk));

        ProjectContextResponse response = service.assembleProjectContext(projectId);

        assertThat(response.decisions()).hasSize(1);
        assertThat(response.requirements()).isEmpty();
        assertThat(response.constraints()).isEmpty();
        assertThat(response.risks()).isEmpty();
        assertThat(response.omittedCounts().stale()).isEqualTo(1);
        assertThat(response.omittedCounts().superseded()).isEqualTo(1);
        assertThat(response.omittedCounts().archived()).isEqualTo(1);
        assertThat(response.omittedCounts().expired()).isEqualTo(1);
        assertThat(response.omittedCounts().sessionSummaries()).isEqualTo(1);
    }

    @Test
    void assembleProjectContext_incrementsAccessOnlyForIncludedEntries() {
        MemoryEntry included = entry(MemoryType.DECISION, MemoryStatus.ACTIVE);
        MemoryEntry excluded = entry(MemoryType.SESSION_SUMMARY, MemoryStatus.ACTIVE);
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId))
                .thenReturn(List.of(included, excluded));

        service.assembleProjectContext(projectId);

        assertThat(included.getAccessCount()).isEqualTo(1);
        assertThat(included.getLastAccessedAt()).isNotNull();
        assertThat(excluded.getAccessCount()).isZero();
        assertThat(excluded.getLastAccessedAt()).isNull();
        verify(memoryEntryRepository).saveAll(List.of(included));
    }

    @Test
    void assembleProjectContext_includesAcceptedAndProposedAdrsOnly() {
        ArchitectureDecision accepted = adr(1, AdrStatus.ACCEPTED);
        ArchitectureDecision proposed = adr(2, AdrStatus.PROPOSED);
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId)).thenReturn(List.of());
        when(adrRepository.findByProjectIdAndStatusInOrderByAdrNumberAsc(
                eq(projectId),
                eq(List.of(AdrStatus.ACCEPTED, AdrStatus.PROPOSED))))
                .thenReturn(List.of(accepted, proposed));

        ProjectContextResponse response = service.assembleProjectContext(projectId);

        assertThat(response.adrs()).extracting("status")
                .containsExactly(AdrStatus.ACCEPTED, AdrStatus.PROPOSED);
    }

    @Test
    void assembleSessionContext_resolvesProjectThroughSessionLink() {
        UUID sessionId = UUID.randomUUID();
        when(sessionLinkRepository.findByPillarAndSessionId(Pillar.LENS, sessionId))
                .thenReturn(Optional.of(ProjectSessionLink.builder().project(project).build()));
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId)).thenReturn(List.of());

        ProjectContextResponse response = service.assembleSessionContext(Pillar.LENS, sessionId);

        assertThat(response.projectId()).isEqualTo(projectId);
    }

    private MemoryEntry entry(MemoryType type, MemoryStatus status) {
        return MemoryEntry.builder()
                .id(UUID.randomUUID())
                .project(project)
                .memoryType(type)
                .tier(MemoryTier.EPISODIC)
                .status(status)
                .content(type.name())
                .accessCount(0)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }

    private ArchitectureDecision adr(int number, AdrStatus status) {
        return ArchitectureDecision.builder()
                .id(UUID.randomUUID())
                .project(project)
                .adrNumber(number)
                .title("ADR " + number)
                .status(status)
                .context("context")
                .decision("decision")
                .createdAt(LocalDateTime.now())
                .build();
    }
}
