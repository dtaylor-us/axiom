package com.memoria.api.service;

import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.MemoryEntryQuery;
import com.memoria.api.dto.ProjectMemorySummaryResponse;
import com.memoria.api.dto.PromoteMemoryEntryRequest;
import com.memoria.api.dto.UpdateMemoryEntryRequest;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MemoryEntryServiceTest {

    private ProjectRepository projectRepository;
    private MemoryEntryRepository memoryEntryRepository;
    private ArchitectureDecisionRepository adrRepository;
    private MemoryEntryService memoryEntryService;
    private UUID projectId;
    private Project project;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        memoryEntryRepository = mock(MemoryEntryRepository.class);
        adrRepository = mock(ArchitectureDecisionRepository.class);
        memoryEntryService = new MemoryEntryService(projectRepository, memoryEntryRepository, adrRepository);
        projectId = UUID.randomUUID();
        project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(memoryEntryRepository.save(any(MemoryEntry.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(adrRepository.save(any(ArchitectureDecision.class))).thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void createEntry_nullExpiresAt_forDecision() {
        MemoryEntry entry = memoryEntryService.createEntry(projectId, request(MemoryType.DECISION));

        assertThat(entry.getExpiresAt()).isNull();
    }

    @Test
    void createEntry_90dayExpiry_forRisk() {
        MemoryEntry entry = memoryEntryService.createEntry(projectId, request(MemoryType.RISK));

        assertExpiryDays(entry, 90);
    }

    @Test
    void createEntry_30dayExpiry_forAssumption() {
        MemoryEntry entry = memoryEntryService.createEntry(projectId, request(MemoryType.ASSUMPTION));

        assertExpiryDays(entry, 30);
    }

    @Test
    void createEntry_14dayExpiry_forSessionSummary() {
        MemoryEntry entry = memoryEntryService.createEntry(projectId, request(MemoryType.SESSION_SUMMARY));

        assertExpiryDays(entry, 14);
    }

    @Test
    void supersede_setsStatusSuperseded() {
        UUID oldEntryId = UUID.randomUUID();
        UUID newEntryId = UUID.randomUUID();
        when(memoryEntryRepository.findById(oldEntryId)).thenReturn(Optional.of(entry(oldEntryId)));
        when(memoryEntryRepository.findById(newEntryId)).thenReturn(Optional.of(entry(newEntryId)));

        MemoryEntry superseded = memoryEntryService.supersede(projectId, oldEntryId, newEntryId);

        assertThat(superseded.getStatus()).isEqualTo(MemoryStatus.SUPERSEDED);
    }

    @Test
    void supersede_setsSupersededByPointer() {
        UUID oldEntryId = UUID.randomUUID();
        UUID newEntryId = UUID.randomUUID();
        when(memoryEntryRepository.findById(oldEntryId)).thenReturn(Optional.of(entry(oldEntryId)));
        when(memoryEntryRepository.findById(newEntryId)).thenReturn(Optional.of(entry(newEntryId)));

        MemoryEntry superseded = memoryEntryService.supersede(projectId, oldEntryId, newEntryId);

        assertThat(superseded.getSupersededBy()).isEqualTo(newEntryId);
    }

    @Test
    void updateEntry_throwsIllegalArgument_whenSettingStatusSuperseded() {
        UUID entryId = UUID.randomUUID();
        when(memoryEntryRepository.findById(entryId)).thenReturn(Optional.of(entry(entryId)));
        UpdateMemoryEntryRequest request = new UpdateMemoryEntryRequest(null, null, null, MemoryStatus.SUPERSEDED);

        assertThatThrownBy(() -> memoryEntryService.updateEntry(projectId, entryId, request))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void markStaleEntries_marksExpiredActiveEntries() {
        MemoryEntry expired = entry(UUID.randomUUID());
        expired.setStatus(MemoryStatus.ACTIVE);
        when(memoryEntryRepository.findByExpiresAtBeforeAndStatus(any(LocalDateTime.class), eq(MemoryStatus.ACTIVE)))
                .thenReturn(List.of(expired));

        memoryEntryService.markStaleEntries();

        assertThat(expired.getStatus()).isEqualTo(MemoryStatus.STALE);
        verify(memoryEntryRepository).saveAll(List.of(expired));
    }

    @Test
    void markStale_setsStatusStale() {
        UUID entryId = UUID.randomUUID();
        MemoryEntry entry = entry(entryId);
        when(memoryEntryRepository.findById(entryId)).thenReturn(Optional.of(entry));

        MemoryEntry stale = memoryEntryService.markStale(projectId, entryId);

        assertThat(stale.getStatus()).isEqualTo(MemoryStatus.STALE);
    }

    @Test
    void archive_setsStatusArchived() {
        UUID entryId = UUID.randomUUID();
        MemoryEntry entry = entry(entryId);
        when(memoryEntryRepository.findById(entryId)).thenReturn(Optional.of(entry));

        MemoryEntry archived = memoryEntryService.archive(projectId, entryId);

        assertThat(archived.getStatus()).isEqualTo(MemoryStatus.ARCHIVED);
    }

    @Test
    void restore_setsStatusActive() {
        UUID entryId = UUID.randomUUID();
        MemoryEntry entry = entry(entryId);
        entry.setStatus(MemoryStatus.STALE);
        when(memoryEntryRepository.findById(entryId)).thenReturn(Optional.of(entry));

        MemoryEntry restored = memoryEntryService.restore(projectId, entryId);

        assertThat(restored.getStatus()).isEqualTo(MemoryStatus.ACTIVE);
    }

    @Test
    void searchEntries_filtersByTypeAndTagAndText() {
        MemoryEntry matching = entry(UUID.randomUUID());
        matching.setMemoryType(MemoryType.RISK);
        matching.setTags(new String[] {"database"});
        matching.setContent("PostgreSQL failover risk");
        when(memoryEntryRepository.findAll(any(Specification.class), any(Sort.class))).thenReturn(List.of(matching));

        List<MemoryEntry> entries = memoryEntryService.searchEntries(
                projectId,
                new MemoryEntryQuery(null, MemoryType.RISK, null, null, "database", null, null, null, "failover"));

        assertThat(entries).containsExactly(matching);
    }

    @Test
    void promoteToAdr_linksAdrToMemoryEntry() {
        UUID entryId = UUID.randomUUID();
        MemoryEntry entry = entry(entryId);
        entry.setContent("Use PostgreSQL for orders");
        when(memoryEntryRepository.findById(entryId)).thenReturn(Optional.of(entry));
        when(adrRepository.findMaxAdrNumberByProjectId(projectId)).thenReturn(Optional.of(2));

        ArchitectureDecision adr = memoryEntryService.promoteToAdr(
                projectId,
                entryId,
                new PromoteMemoryEntryRequest(null, "Context", "Decision", null, null));

        assertThat(adr.getAdrNumber()).isEqualTo(3);
        assertThat(adr.getTitle()).isEqualTo("Use PostgreSQL for orders");
        assertThat(adr.getSourceMemoryEntryId()).isEqualTo(entryId);
    }

    @Test
    void summarizeProject_countsLifecycleAndTypes() {
        MemoryEntry activeRisk = entry(UUID.randomUUID());
        activeRisk.setMemoryType(MemoryType.RISK);
        activeRisk.setStatus(MemoryStatus.ACTIVE);
        activeRisk.setExpiresAt(LocalDateTime.now().plusDays(5));
        MemoryEntry staleDecision = entry(UUID.randomUUID());
        staleDecision.setMemoryType(MemoryType.DECISION);
        staleDecision.setStatus(MemoryStatus.STALE);
        MemoryEntry archivedRequirement = entry(UUID.randomUUID());
        archivedRequirement.setMemoryType(MemoryType.REQUIREMENT);
        archivedRequirement.setStatus(MemoryStatus.ARCHIVED);
        MemoryEntry superseded = entry(UUID.randomUUID());
        superseded.setMemoryType(MemoryType.ASSUMPTION);
        superseded.setStatus(MemoryStatus.SUPERSEDED);
        when(memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId))
                .thenReturn(List.of(activeRisk, staleDecision, archivedRequirement, superseded));
        when(adrRepository.findByProjectIdOrderByAdrNumberAsc(projectId))
                .thenReturn(List.of(ArchitectureDecision.builder().build()));

        ProjectMemorySummaryResponse summary = memoryEntryService.summarizeProject(projectId);

        assertThat(summary.totalFacts()).isEqualTo(4);
        assertThat(summary.activeFacts()).isEqualTo(1);
        assertThat(summary.staleFacts()).isEqualTo(1);
        assertThat(summary.archivedFacts()).isEqualTo(1);
        assertThat(summary.supersededFacts()).isEqualTo(1);
        assertThat(summary.decisions()).isEqualTo(1);
        assertThat(summary.requirements()).isEqualTo(1);
        assertThat(summary.openRisks()).isEqualTo(1);
        assertThat(summary.adrCount()).isEqualTo(1);
        assertThat(summary.expiringSoon()).isEqualTo(1);
    }

    private CreateMemoryEntryRequest request(MemoryType type) {
        return new CreateMemoryEntryRequest(type, MemoryTier.EPISODIC, "content", null, null, null, null, null, null);
    }

    private MemoryEntry entry(UUID id) {
        return MemoryEntry.builder()
                .id(id)
                .project(project)
                .status(MemoryStatus.ACTIVE)
                .content("content")
                .memoryType(MemoryType.DECISION)
                .tier(MemoryTier.EPISODIC)
                .build();
    }

    private void assertExpiryDays(MemoryEntry entry, int days) {
        assertThat(entry.getExpiresAt()).isNotNull();
        long actualDays = Duration.between(entry.getCreatedAt(), entry.getExpiresAt()).toDays();
        assertThat(actualDays).isEqualTo(days);
    }
}
