package com.memoria.api.service;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.UpdateMemoryEntryRequest;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class MemoryEntryService {

    private final ProjectRepository projectRepository;
    private final MemoryEntryRepository memoryEntryRepository;

    @Transactional
    public MemoryEntry createEntry(UUID projectId, CreateMemoryEntryRequest req) {
        Project project = requireProject(projectId);
        LocalDateTime now = LocalDateTime.now();
        MemoryEntry entry = MemoryEntry.builder()
                .project(project)
                .memoryType(req.memoryType())
                .tier(req.tier())
                .content(req.content())
                .rationale(req.rationale())
                .sourcePillar(req.sourcePillar())
                .sourceSessionId(req.sourceSessionId())
                .sourceExcerpt(req.sourceExcerpt())
                .confidence(req.confidence() == null ? MemoryConfidence.MEDIUM : req.confidence())
                .status(MemoryStatus.ACTIVE)
                .expiresAt(expiresAtFor(req.memoryType(), now))
                .accessCount(0)
                .tags(req.tags())
                .createdAt(now)
                .updatedAt(now)
                .build();
        return memoryEntryRepository.save(entry);
    }

    @Transactional(readOnly = true)
    public List<MemoryEntry> listEntries(UUID projectId, MemoryStatus status) {
        requireProject(projectId);
        if (status != null) {
            return memoryEntryRepository.findByProjectIdAndStatusOrderByCreatedAtDesc(projectId, status);
        }
        return memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
    }

    @Transactional
    public MemoryEntry updateEntry(UUID projectId, UUID entryId, UpdateMemoryEntryRequest req) {
        MemoryEntry entry = requireProjectEntry(projectId, entryId);
        if (req.status() == MemoryStatus.SUPERSEDED) {
            throw new IllegalArgumentException("Use supersede() to set status SUPERSEDED");
        }
        if (req.content() != null) {
            entry.setContent(req.content());
        }
        if (req.rationale() != null) {
            entry.setRationale(req.rationale());
        }
        if (req.tags() != null) {
            entry.setTags(req.tags());
        }
        if (req.status() != null) {
            entry.setStatus(req.status());
        }
        entry.setUpdatedAt(LocalDateTime.now());
        return memoryEntryRepository.save(entry);
    }

    @Transactional
    public MemoryEntry supersede(UUID projectId, UUID entryId, UUID newEntryId) {
        MemoryEntry entry = requireProjectEntry(projectId, entryId);
        requireProjectEntry(projectId, newEntryId);
        entry.setStatus(MemoryStatus.SUPERSEDED);
        entry.setSupersededBy(newEntryId);
        entry.setUpdatedAt(LocalDateTime.now());
        return memoryEntryRepository.save(entry);
    }

    @Scheduled(cron = "0 0 2 * * *")
    @Transactional
    public void markStaleEntries() {
        List<MemoryEntry> expiredEntries = memoryEntryRepository.findByExpiresAtBeforeAndStatus(
                LocalDateTime.now(),
                MemoryStatus.ACTIVE);
        expiredEntries.forEach(entry -> {
            entry.setStatus(MemoryStatus.STALE);
            entry.setUpdatedAt(LocalDateTime.now());
        });
        memoryEntryRepository.saveAll(expiredEntries);
    }

    private LocalDateTime expiresAtFor(MemoryType type, LocalDateTime now) {
        return switch (type) {
            case DECISION, REQUIREMENT, CONSTRAINT -> null;
            case RISK -> now.plusDays(90);
            case QUALITY_SCORE -> now.plusDays(60);
            case ASSUMPTION -> now.plusDays(30);
            case SESSION_SUMMARY -> now.plusDays(14);
        };
    }

    private Project requireProject(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));
    }

    private MemoryEntry requireProjectEntry(UUID projectId, UUID entryId) {
        requireProject(projectId);
        MemoryEntry entry = memoryEntryRepository.findById(entryId)
                .orElseThrow(() -> new ResourceNotFoundException("Memory entry not found"));
        if (!entry.getProject().getId().equals(projectId)) {
            throw new ResourceNotFoundException("Memory entry not found");
        }
        return entry;
    }
}
