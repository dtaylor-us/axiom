package com.memoria.api.service;

import com.memoria.api.client.ArchonMemoriaClient;
import com.memoria.api.client.LensMemoriaClient;
import com.memoria.api.client.SpecWeaverMemoriaClient;
import com.memoria.api.domain.model.MemoryConfidence;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.domain.model.MemoryTier;
import com.memoria.api.domain.model.MemoryType;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.dto.AgentConflictFlag;
import com.memoria.api.dto.AgentDistillRequest;
import com.memoria.api.dto.AgentDistillResponse;
import com.memoria.api.dto.AgentMemoryCandidate;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.DistillSessionRequest;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.MemoryEntryRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class DistillationService {

    private final ProjectRepository projectRepository;
    private final ProjectSessionLinkRepository sessionLinkRepository;
    private final MemoryEntryRepository memoryEntryRepository;
    private final MemoryEntryService memoryEntryService;
    private final MemoriaAgentClient memoriaAgentClient;
    private final ArchonMemoriaClient archonClient;
    private final SpecWeaverMemoriaClient specweaverClient;
    private final LensMemoriaClient lensClient;

    @Transactional
    public DistillSessionResponse distillLinkedSession(DistillSessionRequest request) {
        UUID projectId = resolveProjectId(request);
        projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));

        DistillSessionRequest hydratedRequest = hydrateSessionPayload(request);

        List<MemoryEntry> existing = memoryEntryRepository.findByProjectIdAndStatusOrderByCreatedAtDesc(
                projectId,
                MemoryStatus.ACTIVE);
        log.info("DIAG pre-agent: pillar={} sessionId={} projectId={} payloadKeys={} existingCount={}",
                hydratedRequest.pillar(),
                hydratedRequest.sessionId(),
                projectId,
                hydratedRequest.sessionPayload() != null ? hydratedRequest.sessionPayload().keySet() : "null",
                existing.size());
        AgentDistillResponse agentResponse = memoriaAgentClient.distill(AgentDistillRequest.from(
                hydratedRequest.sessionId(),
                projectId,
                hydratedRequest.pillar(),
                hydratedRequest.sessionSummary(),
                hydratedRequest.sessionPayload(),
                existing.stream().map(this::toAgentEntry).toList()));

        if (agentResponse == null) {
            log.error("DIAG agent-response: NULL returned for pillar={} sessionId={}",
                    hydratedRequest.pillar(), hydratedRequest.sessionId());
            throw new IllegalStateException("Distillation agent unavailable");
        } else {
            log.info("DIAG agent-response: pillar={} sessionId={} candidates={} conflicts={} msg={}",
                    hydratedRequest.pillar(),
                    hydratedRequest.sessionId(),
                    agentResponse.candidates() == null ? "null" : agentResponse.candidates().size(),
                    agentResponse.conflicts() == null ? "null" : agentResponse.conflicts().size(),
                    agentResponse.message());
        }

        List<AgentMemoryCandidate> candidates = agentResponse.candidates() == null
                ? List.of()
                : agentResponse.candidates();
        List<MemoryEntry> created = new ArrayList<>();
        Map<Integer, MemoryEntry> createdByCandidateIndex = new HashMap<>();
        for (int index = 0; index < candidates.size(); index++) {
            AgentMemoryCandidate candidate = candidates.get(index);
            if (isDuplicate(existing, created, hydratedRequest, candidate)) {
                continue;
            }
            MemoryEntry entry = memoryEntryService.createEntry(projectId, toCreateRequest(hydratedRequest, candidate));
            created.add(entry);
            createdByCandidateIndex.put(index, entry);
        }
        log.info("DIAG candidate-result: pillar={} sessionId={} total={} created={} duplicatesDropped={}",
                hydratedRequest.pillar(), hydratedRequest.sessionId(), candidates.size(), created.size(),
                candidates.size() - created.size());

        int superseded = applySupersession(projectId, createdByCandidateIndex, agentResponse);
        return new DistillSessionResponse(
                projectId,
                request.sessionId(),
                candidates.size(),
                created.size(),
                superseded,
                created.stream().map(ResponseMapper::toMemoryEntryResponse).toList(),
                agentResponse.message());
    }

    private DistillSessionRequest hydrateSessionPayload(DistillSessionRequest request) {
        boolean hasSummary = request.sessionSummary() != null && !request.sessionSummary().isBlank();
        boolean hasPayload = request.sessionPayload() != null && !request.sessionPayload().isEmpty();
        if (hasSummary || hasPayload) {
            return request;
        }

        Optional<Map<String, Object>> payload = switch (request.pillar()) {
            case ARCHON -> archonClient.getConversationOutput(request.sessionId());
            case SPECWEAVER -> specweaverClient.getSessionPackage(request.sessionId());
            case LENS -> lensClient.getReviewReport(request.sessionId());
        };
        if (payload.isEmpty() || payload.get().isEmpty()) {
            throw new IllegalStateException("Session payload unavailable for distillation");
        }
        return new DistillSessionRequest(
                request.projectId(), request.pillar(), request.sessionId(), request.sessionSummary(), payload.get());
    }

    private UUID resolveProjectId(DistillSessionRequest request) {
        if (request.projectId() != null) {
            return request.projectId();
        }
        return sessionLinkRepository.findByPillarAndSessionId(request.pillar(), request.sessionId())
                .map(link -> link.getProject().getId())
                .orElseThrow(() -> new ResourceNotFoundException("Linked Memoria project not found for session"));
    }

    private CreateMemoryEntryRequest toCreateRequest(DistillSessionRequest request, AgentMemoryCandidate candidate) {
        return new CreateMemoryEntryRequest(
                enumValue(MemoryType.class, candidate.memoryType(), MemoryType.SESSION_SUMMARY),
                MemoryTier.EPISODIC,
                candidate.content(),
                candidate.rationale(),
                request.pillar(),
                request.sessionId(),
                candidate.sourceExcerpt(),
                enumValue(MemoryConfidence.class, candidate.confidence(), MemoryConfidence.MEDIUM),
                candidate.tags() == null ? new String[0] : candidate.tags().toArray(String[]::new));
    }

    private int applySupersession(
            UUID projectId,
            Map<Integer, MemoryEntry> createdByCandidateIndex,
            AgentDistillResponse agentResponse) {
        if (agentResponse == null || agentResponse.conflicts() == null || createdByCandidateIndex.isEmpty()) {
            return 0;
        }
        int superseded = 0;
        for (AgentConflictFlag conflict : agentResponse.conflicts()) {
            if (!conflict.supersedes() || !createdByCandidateIndex.containsKey(conflict.newCandidateIndex())) {
                continue;
            }
            try {
                UUID oldEntryId = UUID.fromString(conflict.existingEntryId());
                UUID newEntryId = createdByCandidateIndex.get(conflict.newCandidateIndex()).getId();
                if (newEntryId != null) {
                    memoryEntryService.supersede(projectId, oldEntryId, newEntryId);
                    superseded++;
                }
            } catch (RuntimeException ignored) {
                // Bad agent conflict references are ignored; memory creation remains valid.
            }
        }
        return superseded;
    }

    private boolean isDuplicate(
            List<MemoryEntry> existing,
            List<MemoryEntry> created,
            DistillSessionRequest request,
            AgentMemoryCandidate candidate) {
        String content = normalize(candidate.content());
        if (content.isBlank()) {
            return true;
        }
        return existing.stream().anyMatch(entry -> sameSourceAndContent(entry, request, content))
                || created.stream().anyMatch(entry -> normalize(entry.getContent()).equals(content));
    }

    private boolean sameSourceAndContent(MemoryEntry entry, DistillSessionRequest request, String content) {
        return entry.getSourcePillar() == request.pillar()
                && request.sessionId().equals(entry.getSourceSessionId())
                && normalize(entry.getContent()).equals(content);
    }

    private Map<String, Object> toAgentEntry(MemoryEntry entry) {
        return Map.of(
                "id", entry.getId().toString(),
                "memoryType", entry.getMemoryType().name(),
                "content", entry.getContent(),
                "tags", entry.getTags() == null ? List.of() : List.of(entry.getTags()));
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
    }

    private <T extends Enum<T>> T enumValue(Class<T> type, String raw, T fallback) {
        if (raw == null || raw.isBlank()) {
            return fallback;
        }
        try {
            return Enum.valueOf(type, raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return fallback;
        }
    }
}
