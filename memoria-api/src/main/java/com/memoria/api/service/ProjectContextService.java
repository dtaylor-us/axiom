package com.memoria.api.service;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.dto.ContextAdrItem;
import com.memoria.api.dto.ContextMemoryItem;
import com.memoria.api.dto.ContextOmittedCounts;
import com.memoria.api.dto.ProjectContextResponse;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ProjectContextService {

    private final ProjectRepository projectRepository;
    private final MemoryEntryRepository memoryEntryRepository;
    private final ArchitectureDecisionRepository adrRepository;
    private final ProjectSessionLinkRepository sessionLinkRepository;

    @Transactional
    public ProjectContextResponse assembleProjectContext(UUID projectId) {
        projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));

        LocalDateTime now = LocalDateTime.now();
        List<MemoryEntry> entries = memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
        List<MemoryEntry> included = entries.stream()
                .filter(entry -> entry.getStatus() == MemoryStatus.ACTIVE)
                .filter(entry -> entry.getMemoryType() != MemoryType.SESSION_SUMMARY)
                .filter(entry -> entry.getExpiresAt() == null || !entry.getExpiresAt().isBefore(now))
                .filter(entry -> isContextType(entry.getMemoryType()))
                .toList();

        included.forEach(entry -> {
            entry.setAccessCount(entry.getAccessCount() + 1);
            entry.setLastAccessedAt(now);
        });
        memoryEntryRepository.saveAll(included);

        List<ContextAdrItem> adrs = adrRepository.findByProjectIdAndStatusInOrderByAdrNumberAsc(
                        projectId,
                        List.of(AdrStatus.ACCEPTED, AdrStatus.PROPOSED))
                .stream()
                .map(this::toAdrItem)
                .toList();

        return new ProjectContextResponse(
                projectId,
                now,
                itemsByType(included, MemoryType.DECISION),
                itemsByType(included, MemoryType.REQUIREMENT),
                itemsByType(included, MemoryType.CONSTRAINT),
                itemsByType(included, MemoryType.RISK),
                itemsByType(included, MemoryType.QUALITY_SCORE),
                adrs,
                omittedCounts(entries, now));
    }

    @Transactional
    public ProjectContextResponse assembleSessionContext(Pillar pillar, UUID sessionId) {
        UUID projectId = sessionLinkRepository.findByPillarAndSessionId(pillar, sessionId)
                .map(link -> link.getProject().getId())
                .orElseThrow(() -> new ResourceNotFoundException("Linked Memoria project not found for session"));
        return assembleProjectContext(projectId);
    }

    private boolean isContextType(MemoryType type) {
        return type == MemoryType.DECISION
                || type == MemoryType.REQUIREMENT
                || type == MemoryType.CONSTRAINT
                || type == MemoryType.RISK
                || type == MemoryType.QUALITY_SCORE;
    }

    private List<ContextMemoryItem> itemsByType(List<MemoryEntry> entries, MemoryType type) {
        return entries.stream()
                .filter(entry -> entry.getMemoryType() == type)
                .map(this::toMemoryItem)
                .toList();
    }

    private ContextOmittedCounts omittedCounts(List<MemoryEntry> entries, LocalDateTime now) {
        return new ContextOmittedCounts(
                countStatus(entries, MemoryStatus.STALE),
                countStatus(entries, MemoryStatus.SUPERSEDED),
                countStatus(entries, MemoryStatus.ARCHIVED),
                entries.stream()
                        .filter(entry -> entry.getStatus() == MemoryStatus.ACTIVE)
                        .filter(entry -> entry.getExpiresAt() != null && entry.getExpiresAt().isBefore(now))
                        .count(),
                entries.stream()
                        .filter(entry -> entry.getMemoryType() == MemoryType.SESSION_SUMMARY)
                        .count());
    }

    private long countStatus(List<MemoryEntry> entries, MemoryStatus status) {
        return entries.stream().filter(entry -> entry.getStatus() == status).count();
    }

    private ContextMemoryItem toMemoryItem(MemoryEntry entry) {
        return new ContextMemoryItem(
                entry.getId(),
                entry.getMemoryType(),
                entry.getContent(),
                entry.getRationale(),
                entry.getSourcePillar(),
                entry.getSourceSessionId(),
                entry.getSourceExcerpt(),
                entry.getConfidence(),
                entry.getExpiresAt(),
                entry.getTags(),
                entry.getCreatedAt());
    }

    private ContextAdrItem toAdrItem(ArchitectureDecision adr) {
        return new ContextAdrItem(
                adr.getId(),
                adr.getAdrNumber(),
                adr.getTitle(),
                adr.getStatus(),
                adr.getContext(),
                adr.getDecision(),
                adr.getConsequences(),
                adr.getAlternativesConsidered(),
                adr.getSourcePillar(),
                adr.getSourceSessionId(),
                adr.getSourceMemoryEntryId(),
                adr.getSupersededByAdrNumber(),
                adr.getCreatedAt());
    }
}
