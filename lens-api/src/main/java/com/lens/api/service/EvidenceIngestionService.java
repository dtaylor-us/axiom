package com.lens.api.service;

import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.domain.model.EvidenceType;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public class EvidenceIngestionService {

    private final Map<UUID, List<ArchitectureEvidence>> evidenceBySession = new LinkedHashMap<>();

    public ArchitectureEvidence submitEvidence(UUID sessionId, EvidenceType evidenceType, String content, String sourceLabel) {
        ArchitectureEvidence evidence = new ArchitectureEvidence(
            UUID.randomUUID(),
            sessionId,
            evidenceType,
            content,
            sourceLabel,
            LocalDateTime.now()
        );
        evidenceBySession.computeIfAbsent(sessionId, ignored -> new ArrayList<>()).add(evidence);
        return evidence;
    }

    public List<ArchitectureEvidence> listEvidence(UUID sessionId) {
        return evidenceBySession.getOrDefault(sessionId, List.of());
    }

    public void deleteEvidence(UUID sessionId, UUID evidenceId) {
        evidenceBySession.computeIfPresent(sessionId, (ignored, items) -> {
            items.removeIf(item -> item.id().equals(evidenceId));
            return items;
        });
    }
}
