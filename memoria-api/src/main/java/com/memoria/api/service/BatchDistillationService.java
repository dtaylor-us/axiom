package com.memoria.api.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.memoria.api.client.ArchonMemoriaClient;
import com.memoria.api.client.LensMemoriaClient;
import com.memoria.api.client.SpecWeaverMemoriaClient;
import com.memoria.api.domain.model.DistillationJob;
import com.memoria.api.domain.model.DistillationJobStatus;
import com.memoria.api.domain.model.Pillar;
import com.memoria.api.domain.model.ProjectSessionLink;
import com.memoria.api.dto.DistillSessionRequest;
import com.memoria.api.dto.DistillSessionResponse;
import com.memoria.api.dto.SessionDistillResult;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.DistillationJobRepository;
import com.memoria.api.repository.ProjectRepository;
import com.memoria.api.repository.ProjectSessionLinkRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class BatchDistillationService {

    private final ProjectRepository projectRepository;
    private final ProjectSessionLinkRepository sessionLinkRepository;
    private final DistillationJobRepository distillationJobRepository;
    private final DistillationService distillationService;
    private final ArchonMemoriaClient archonClient;
    private final SpecWeaverMemoriaClient specweaverClient;
    private final LensMemoriaClient lensClient;
    private final ObjectMapper objectMapper;

    @Transactional
    public DistillationJob distillAllLinkedSessions(UUID projectId) {
        projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));

        List<ProjectSessionLink> linkedSessions = sessionLinkRepository.findByProjectId(projectId);

        DistillationJob job = distillationJobRepository.save(
                DistillationJob.builder()
                        .project(projectRepository.getReferenceById(projectId))
                        .status(DistillationJobStatus.RUNNING)
                        .sessionCount(linkedSessions.size())
                        .totalCandidates(0)
                        .totalPersisted(0)
                        .totalSuperseded(0)
                        .totalConflicts(0)
                        .sessionResults("[]")
                        .createdAt(LocalDateTime.now())
                        .build());

        if (linkedSessions.isEmpty()) {
            job.setStatus(DistillationJobStatus.COMPLETE);
            job.setCompletedAt(LocalDateTime.now());
            return distillationJobRepository.save(job);
        }

        List<SessionDistillResult> sessionResults = new ArrayList<>();
        int successCount = 0;
        int failCount = 0;

        for (ProjectSessionLink link : linkedSessions) {
            SessionDistillResult result = processLinkedSession(projectId, link);
            sessionResults.add(result);

            if ("SUCCESS".equals(result.status())) {
                successCount++;
                job.setTotalCandidates(job.getTotalCandidates() + result.candidates());
                job.setTotalPersisted(job.getTotalPersisted() + result.persisted());
                job.setTotalSuperseded(job.getTotalSuperseded() + result.superseded());
                job.setTotalConflicts(job.getTotalConflicts() + result.conflicts());
            } else {
                failCount++;
            }
        }

        DistillationJobStatus finalStatus;
        if (failCount == 0) {
            finalStatus = DistillationJobStatus.COMPLETE;
        } else if (successCount == 0) {
            finalStatus = DistillationJobStatus.FAILED;
        } else {
            finalStatus = DistillationJobStatus.PARTIAL;
        }

        job.setStatus(finalStatus);
        job.setCompletedAt(LocalDateTime.now());
        job.setSessionResults(serializeResults(sessionResults));
        return distillationJobRepository.save(job);
    }

    @Transactional(readOnly = true)
    public List<DistillationJob> listJobs(UUID projectId, int limit) {
        return distillationJobRepository
                .findByProjectIdOrderByCreatedAtDesc(projectId)
                .stream()
                .limit(limit)
                .toList();
    }

    private SessionDistillResult processLinkedSession(UUID projectId, ProjectSessionLink link) {
        UUID sessionId = link.getSessionId();
        Pillar pillar = link.getPillar();

        Optional<Map<String, Object>> payloadOpt = fetchSessionPayload(pillar, sessionId);
        if (payloadOpt.isEmpty()) {
            log.warn("Skipping session — payload unavailable pillar={} sessionId={}", pillar, sessionId);
            return new SessionDistillResult(sessionId, pillar.name(), "SKIPPED", 0, 0, 0, 0, "Payload unavailable");
        }

        try {
            DistillSessionRequest request = new DistillSessionRequest(
                    projectId, pillar, sessionId, null, payloadOpt.get());
            DistillSessionResponse response = distillationService.distillLinkedSession(request);
            return new SessionDistillResult(
                    sessionId,
                    pillar.name(),
                    "SUCCESS",
                    response.candidatesReceived(),
                    response.entriesCreated(),
                    response.entriesSuperseded(),
                    0,
                    null);
        } catch (Exception ex) {
            log.warn("Distillation failed pillar={} sessionId={} error={}",
                    pillar, sessionId, ex.getMessage());
            return new SessionDistillResult(
                    sessionId, pillar.name(), "FAILED", 0, 0, 0, 0,
                    ex.getMessage() == null ? "Unknown error" : ex.getMessage());
        }
    }

    private Optional<Map<String, Object>> fetchSessionPayload(Pillar pillar, UUID sessionId) {
        try {
            return switch (pillar) {
                case ARCHON -> archonClient.getConversationOutput(sessionId);
                case SPECWEAVER -> specweaverClient.getSessionPackage(sessionId);
                case LENS -> lensClient.getReviewReport(sessionId);
            };
        } catch (Exception ex) {
            log.warn("Failed to fetch payload pillar={} session={} error={}",
                    pillar, sessionId, ex.getMessage());
            return Optional.empty();
        }
    }

    private String serializeResults(List<SessionDistillResult> results) {
        try {
            return objectMapper.writeValueAsString(results);
        } catch (Exception ex) {
            log.error("Failed to serialize session results: {}", ex.getMessage());
            return "[]";
        }
    }
}
