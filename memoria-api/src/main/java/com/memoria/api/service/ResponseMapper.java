package com.memoria.api.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.DistillationJob;
import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.Project;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.dto.ArchitectureDecisionResponse;
import com.memoria.api.dto.DistillationJobResponse;
import com.memoria.api.dto.MemoryEntryResponse;
import com.memoria.api.dto.ProjectResponse;
import com.memoria.api.dto.SessionDistillResult;
import com.memoria.api.dto.SessionLinkResponse;

import java.util.List;

public final class ResponseMapper {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper()
            .findAndRegisterModules();

    private ResponseMapper() {
    }

    public static ProjectResponse toProjectResponse(Project project) {
        return new ProjectResponse(
                project.getId(),
                project.getName(),
                project.getDescription(),
                project.getStatus(),
                project.getCreatedAt(),
                project.getUpdatedAt());
    }

    public static SessionLinkResponse toSessionLinkResponse(ProjectSessionLink link) {
        return new SessionLinkResponse(
                link.getId(),
                link.getProject().getId(),
                link.getPillar(),
                link.getSessionId(),
                link.getLinkedAt());
    }

    public static MemoryEntryResponse toMemoryEntryResponse(MemoryEntry entry) {
        return new MemoryEntryResponse(
                entry.getId(),
                entry.getProject().getId(),
                entry.getMemoryType(),
                entry.getTier(),
                entry.getContent(),
                entry.getRationale(),
                entry.getSourcePillar(),
                entry.getSourceSessionId(),
                entry.getSourceExcerpt(),
                entry.getConfidence(),
                entry.getStatus(),
                entry.getSupersededBy(),
                entry.getExpiresAt(),
                entry.getLastAccessedAt(),
                entry.getAccessCount(),
                entry.getTags(),
                entry.getCreatedAt(),
                entry.getUpdatedAt());
    }

    public static ArchitectureDecisionResponse toArchitectureDecisionResponse(ArchitectureDecision adr) {
        return new ArchitectureDecisionResponse(
                adr.getId(),
                adr.getProject().getId(),
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

    public static DistillationJobResponse toDistillationJobResponse(DistillationJob job) {
        List<SessionDistillResult> sessionResults = deserializeSessionResults(job.getSessionResults());
        return new DistillationJobResponse(
                job.getId(),
                job.getProject().getId(),
                job.getStatus().name(),
                job.getSessionCount(),
                job.getTotalCandidates(),
                job.getTotalPersisted(),
                job.getTotalSuperseded(),
                job.getTotalConflicts(),
                sessionResults,
                job.getCreatedAt(),
                job.getCompletedAt());
    }

    private static List<SessionDistillResult> deserializeSessionResults(String json) {
        if (json == null || json.isBlank() || "[]".equals(json.trim())) {
            return List.of();
        }
        try {
            return OBJECT_MAPPER.readValue(json, new TypeReference<List<SessionDistillResult>>() {});
        } catch (Exception ex) {
            return List.of();
        }
    }
}
