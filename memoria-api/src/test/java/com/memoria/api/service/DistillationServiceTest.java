package com.memoria.api.service;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.dto.AgentConflictFlag;
import com.memoria.api.dto.AgentDistillResponse;
import com.memoria.api.dto.AgentMemoryCandidate;
import com.memoria.api.dto.DistillSessionRequest;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class DistillationServiceTest {

    private ProjectRepository projectRepository;
    private ProjectSessionLinkRepository sessionLinkRepository;
    private MemoryEntryRepository memoryEntryRepository;
    private MemoriaAgentClient memoriaAgentClient;
    private DistillationService distillationService;
    private UUID projectId;
    private UUID sessionId;
    private Project project;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        sessionLinkRepository = mock(ProjectSessionLinkRepository.class);
        memoryEntryRepository = mock(MemoryEntryRepository.class);
        ArchitectureDecisionRepository adrRepository = mock(ArchitectureDecisionRepository.class);
        memoriaAgentClient = mock(MemoriaAgentClient.class);
        MemoryEntryService memoryEntryService = new MemoryEntryService(projectRepository, memoryEntryRepository, adrRepository);
        distillationService = new DistillationService(
                projectRepository,
                sessionLinkRepository,
                memoryEntryRepository,
                memoryEntryService,
                memoriaAgentClient);
        projectId = UUID.randomUUID();
        sessionId = UUID.randomUUID();
        project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        Map<UUID, MemoryEntry> savedEntries = new HashMap<>();
        when(memoryEntryRepository.save(any(MemoryEntry.class))).thenAnswer(invocation -> {
            MemoryEntry entry = invocation.getArgument(0);
            if (entry.getId() == null) {
                entry.setId(UUID.randomUUID());
            }
            savedEntries.put(entry.getId(), entry);
            when(memoryEntryRepository.findById(entry.getId())).thenReturn(Optional.of(entry));
            return entry;
        });
    }

    @Test
    void distillLinkedSession_resolvesProjectFromSessionLink() {
        when(sessionLinkRepository.findByPillarAndSessionId(Pillar.ARCHON, sessionId))
                .thenReturn(Optional.of(ProjectSessionLink.builder().project(project).build()));
        when(memoryEntryRepository.findByProjectIdAndStatusOrderByCreatedAtDesc(projectId, MemoryStatus.ACTIVE))
                .thenReturn(List.of());
        when(memoriaAgentClient.distill(any())).thenReturn(new AgentDistillResponse(
                sessionId.toString(),
                List.of(new AgentMemoryCandidate(
                        "DECISION",
                        "Use PostgreSQL",
                        "Consistency matters",
                        "HIGH",
                        "Decision: Use PostgreSQL",
                        List.of("database"))),
                List.of(),
                "ok"));

        DistillSessionResponse response = distillationService.distillLinkedSession(new DistillSessionRequest(
                null,
                Pillar.ARCHON,
                sessionId,
                "Decision: Use PostgreSQL",
                Map.of()));

        assertThat(response.projectId()).isEqualTo(projectId);
        assertThat(response.entriesCreated()).isEqualTo(1);
        assertThat(response.createdEntries().getFirst().memoryType()).isEqualTo(MemoryType.DECISION);
        assertThat(response.createdEntries().getFirst().confidence()).isEqualTo(MemoryConfidence.HIGH);
    }

    @Test
    void distillLinkedSession_supersedesExistingEntryAfterCreatingReplacement() {
        UUID oldEntryId = UUID.randomUUID();
        MemoryEntry existing = MemoryEntry.builder()
                .id(oldEntryId)
                .project(project)
                .memoryType(MemoryType.REQUIREMENT)
                .tier(MemoryTier.EPISODIC)
                .status(MemoryStatus.ACTIVE)
                .content("Use PostgreSQL for order storage")
                .sourcePillar(Pillar.SPECWEAVER)
                .sourceSessionId(UUID.randomUUID())
                .build();
        when(memoryEntryRepository.findByProjectIdAndStatusOrderByCreatedAtDesc(projectId, MemoryStatus.ACTIVE))
                .thenReturn(List.of(existing));
        when(memoryEntryRepository.findById(oldEntryId)).thenReturn(Optional.of(existing));
        when(memoriaAgentClient.distill(any())).thenReturn(new AgentDistillResponse(
                sessionId.toString(),
                List.of(new AgentMemoryCandidate(
                        "REQUIREMENT",
                        "Use Azure SQL instead of PostgreSQL for order storage",
                        "Updated requirement",
                        "MEDIUM",
                        null,
                        List.of("orders"))),
                List.of(new AgentConflictFlag(oldEntryId.toString(), 0, "replacement", true)),
                "ok"));

        DistillSessionResponse response = distillationService.distillLinkedSession(new DistillSessionRequest(
                projectId,
                Pillar.SPECWEAVER,
                sessionId,
                null,
                Map.of()));

        assertThat(response.entriesSuperseded()).isEqualTo(1);
        assertThat(existing.getStatus()).isEqualTo(MemoryStatus.SUPERSEDED);
        verify(memoryEntryRepository).save(existing);
    }
}
