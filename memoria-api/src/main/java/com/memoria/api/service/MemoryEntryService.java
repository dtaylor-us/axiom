package com.memoria.api.service;

import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.MemoryEntryQuery;
import com.memoria.api.dto.ProjectMemorySummaryResponse;
import com.memoria.api.dto.PromoteMemoryEntryRequest;
import com.memoria.api.dto.UpdateMemoryEntryRequest;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import jakarta.persistence.criteria.Predicate;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Sort;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class MemoryEntryService {

    private final ProjectRepository projectRepository;
    private final MemoryEntryRepository memoryEntryRepository;
    private final ArchitectureDecisionRepository adrRepository;

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

    @Transactional(readOnly = true)
    public List<MemoryEntry> searchEntries(UUID projectId, MemoryEntryQuery query) {
        requireProject(projectId);
        String normalizedTextQuery = query.q() == null ? null : query.q().trim().toLowerCase();
        return memoryEntryRepository
                .findAll((root, criteriaQuery, criteriaBuilder) -> {
                    List<Predicate> predicates = new ArrayList<>();
                    predicates.add(criteriaBuilder.equal(root.get("project").get("id"), projectId));
                    if (query.status() != null) {
                        predicates.add(criteriaBuilder.equal(root.get("status"), query.status()));
                    }
                    if (query.memoryType() != null) {
                        predicates.add(criteriaBuilder.equal(root.get("memoryType"), query.memoryType()));
                    }
                    if (query.tier() != null) {
                        predicates.add(criteriaBuilder.equal(root.get("tier"), query.tier()));
                    }
                    if (query.sourcePillar() != null) {
                        predicates.add(criteriaBuilder.equal(root.get("sourcePillar"), query.sourcePillar()));
                    }
                    if (query.createdAfter() != null) {
                        predicates.add(criteriaBuilder.greaterThanOrEqualTo(root.get("createdAt"), query.createdAfter()));
                    }
                    if (query.createdBefore() != null) {
                        predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("createdAt"), query.createdBefore()));
                    }
                    if (query.expiresBefore() != null) {
                        predicates.add(criteriaBuilder.lessThanOrEqualTo(root.get("expiresAt"), query.expiresBefore()));
                    }
                    if (normalizedTextQuery != null && !normalizedTextQuery.isBlank()) {
                        String textLike = "%" + normalizedTextQuery + "%";
                        predicates.add(criteriaBuilder.or(
                                criteriaBuilder.like(criteriaBuilder.lower(root.get("content")), textLike),
                                criteriaBuilder.like(criteriaBuilder.lower(root.get("rationale")), textLike),
                                criteriaBuilder.like(criteriaBuilder.lower(root.get("sourceExcerpt")), textLike)));
                    }
                    return criteriaBuilder.and(predicates.toArray(new Predicate[0]));
                }, Sort.by(Sort.Direction.DESC, "createdAt"))
                .stream()
                .filter(entry -> matchesTag(entry, query.tag()))
                .toList();
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

    @Transactional
    public MemoryEntry markStale(UUID projectId, UUID entryId) {
        return transition(projectId, entryId, MemoryStatus.STALE);
    }

    @Transactional
    public MemoryEntry archive(UUID projectId, UUID entryId) {
        return transition(projectId, entryId, MemoryStatus.ARCHIVED);
    }

    @Transactional
    public MemoryEntry restore(UUID projectId, UUID entryId) {
        return transition(projectId, entryId, MemoryStatus.ACTIVE);
    }

    @Transactional
    public com.memoria.api.domain.model.ArchitectureDecision promoteToAdr(
            UUID projectId,
            UUID entryId,
            PromoteMemoryEntryRequest req) {
        Project project = requireProject(projectId);
        MemoryEntry entry = requireProjectEntry(projectId, entryId);
        int adrNumber = adrRepository.findMaxAdrNumberByProjectId(projectId).orElse(0) + 1;
        String title = req.title() == null || req.title().isBlank()
                ? titleFromMemory(entry)
                : req.title();
        com.memoria.api.domain.model.ArchitectureDecision adr =
                com.memoria.api.domain.model.ArchitectureDecision.builder()
                        .project(project)
                        .adrNumber(adrNumber)
                        .title(title)
                        .context(req.context())
                        .decision(req.decision())
                        .consequences(req.consequences())
                        .alternativesConsidered(req.alternativesConsidered())
                        .sourcePillar(entry.getSourcePillar())
                        .sourceSessionId(entry.getSourceSessionId())
                        .sourceMemoryEntryId(entry.getId())
                        .createdAt(LocalDateTime.now())
                        .build();
        return adrRepository.save(adr);
    }

    @Transactional(readOnly = true)
    public ProjectMemorySummaryResponse summarizeProject(UUID projectId) {
        requireProject(projectId);
        List<MemoryEntry> entries = memoryEntryRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
        LocalDateTime expiringSoonCutoff = LocalDateTime.now().plusDays(14);
        return new ProjectMemorySummaryResponse(
                entries.size(),
                countStatus(entries, MemoryStatus.ACTIVE),
                countStatus(entries, MemoryStatus.STALE),
                countStatus(entries, MemoryStatus.ARCHIVED),
                countStatus(entries, MemoryStatus.SUPERSEDED),
                entries.stream().filter(entry -> entry.getMemoryType() == MemoryType.DECISION).count(),
                entries.stream().filter(entry -> entry.getMemoryType() == MemoryType.REQUIREMENT).count(),
                entries.stream()
                        .filter(entry -> entry.getMemoryType() == MemoryType.RISK)
                        .filter(entry -> entry.getStatus() == MemoryStatus.ACTIVE)
                        .count(),
                adrRepository.findByProjectIdOrderByAdrNumberAsc(projectId).size(),
                entries.stream()
                        .filter(entry -> entry.getStatus() == MemoryStatus.ACTIVE)
                        .filter(entry -> entry.getExpiresAt() != null)
                        .filter(entry -> !entry.getExpiresAt().isAfter(expiringSoonCutoff))
                        .count());
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

    private MemoryEntry transition(UUID projectId, UUID entryId, MemoryStatus status) {
        MemoryEntry entry = requireProjectEntry(projectId, entryId);
        if (status == MemoryStatus.SUPERSEDED) {
            throw new IllegalArgumentException("Use supersede() to set status SUPERSEDED");
        }
        entry.setStatus(status);
        entry.setUpdatedAt(LocalDateTime.now());
        return memoryEntryRepository.save(entry);
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

    private boolean matchesTag(MemoryEntry entry, String tag) {
        if (tag == null || tag.isBlank()) {
            return true;
        }
        if (entry.getTags() == null) {
            return false;
        }
        for (String entryTag : entry.getTags()) {
            if (entryTag.equalsIgnoreCase(tag.trim())) {
                return true;
            }
        }
        return false;
    }

    private long countStatus(List<MemoryEntry> entries, MemoryStatus status) {
        return entries.stream().filter(entry -> entry.getStatus() == status).count();
    }

    private String titleFromMemory(MemoryEntry entry) {
        String content = entry.getContent().trim();
        if (content.length() <= 80) {
            return content;
        }
        return content.substring(0, 77) + "...";
    }
}
