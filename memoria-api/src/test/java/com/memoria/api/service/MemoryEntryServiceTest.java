package com.memoria.api.service;

import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.UpdateMemoryEntryRequest;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

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
    private MemoryEntryService memoryEntryService;
    private UUID projectId;
    private Project project;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        memoryEntryRepository = mock(MemoryEntryRepository.class);
        memoryEntryService = new MemoryEntryService(projectRepository, memoryEntryRepository);
        projectId = UUID.randomUUID();
        project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(memoryEntryRepository.save(any(MemoryEntry.class))).thenAnswer(invocation -> invocation.getArgument(0));
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
