package com.specweaver.api.service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.specweaver.api.agent.AgentExtractionRequest;
import com.specweaver.api.agent.AgentExtractionResponse;
import com.specweaver.api.agent.SpecWeaverAgentClient;
import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.GeneratedPackage;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionDocument;
import com.specweaver.api.domain.model.SessionStatus;
import com.specweaver.api.dto.ArchInputPackageDto;
import com.specweaver.api.dto.GapAreaDto;
import com.specweaver.api.dto.response.PackageResponse;
import com.specweaver.api.exception.AgentCommunicationException;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.repository.GeneratedPackageRepository;
import com.specweaver.api.repository.SessionDocumentRepository;
import com.specweaver.api.repository.SessionRepository;

/**
 * Builds ArchInputPackages by delegating extracted text to specweaver-agent.
 *
 * @author OpenAI
 */
@Service
@RequiredArgsConstructor
public class PackageGenerationService {

    private final SessionService sessionService;
    private final SessionRepository sessionRepository;
    private final SessionDocumentRepository documentRepository;
    private final GeneratedPackageRepository packageRepository;
    private final SpecWeaverAgentClient agentClient;
    private final ObjectMapper objectMapper;
    private final ReadinessScoreService readinessScoreService;
    private final BriefFormatter briefFormatter;

    @Transactional
    public PackageResponse generatePackage(UUID sessionId, UUID userId) {
        Session session = sessionService.requireOwnedSession(sessionId, userId);
        if (session.getStatus() == SessionStatus.PROCESSING) {
            throw new IllegalStateException("Package generation already in progress");
        }
        List<SessionDocument> documents = documentRepository
                .findBySessionIdAndStatusOrderByCreatedAtAsc(sessionId, DocumentStatus.EXTRACTED);
        if (documents.isEmpty()) {
            throw new IllegalArgumentException("No extracted documents available for package generation");
        }

        session.setStatus(SessionStatus.PROCESSING);
        sessionRepository.save(session);
        try {
            AgentExtractionResponse response = agentClient.extract(toAgentRequest(sessionId, documents));
            if (response == null || !response.success()) {
                String message = response == null ? "Agent returned no response" : response.errorMessage();
                throw new AgentCommunicationException(message);
            }
            GeneratedPackage generatedPackage = packageRepository.findBySessionId(sessionId)
                    .orElseGet(() -> GeneratedPackage.builder().session(session).build());
            generatedPackage.setPackageJson(response.archInputPackageJson());
                ArchInputPackageDto packageDto = parsePackage(response.archInputPackageJson());
                PackageMetrics metrics = extractPackageMetrics(packageDto);
            generatedPackage.setTotalRequirements(metrics.totalRequirements());
            generatedPackage.setHighConfidenceCount(metrics.highConfidenceCount());
            generatedPackage.setInferredCount(metrics.inferredCount());
            generatedPackage.setDuplicateCount(metrics.duplicateCount());
            generatedPackage.setGapCount(metrics.gapCount());
            generatedPackage.setConflictCount(metrics.conflictCount());
            generatedPackage.setReadinessScore(metrics.readinessScore());
                generatedPackage.setBriefText(briefFormatter.format(packageDto, session));
            GeneratedPackage saved = packageRepository.save(generatedPackage);
            session.setStatus(SessionStatus.PACKAGE_READY);
            sessionRepository.save(session);
            return ResponseMapper.toPackageResponse(saved, objectMapper);
        } catch (RuntimeException e) {
            session.setStatus(SessionStatus.ACTIVE);
            sessionRepository.save(session);
            throw e;
        }
    }

    @Transactional(readOnly = true)
    public PackageResponse getPackage(UUID sessionId, UUID userId) {
        sessionService.requireOwnedSession(sessionId, userId);
        return packageRepository.findBySessionId(sessionId)
                .map(generatedPackage -> ResponseMapper.toPackageResponse(generatedPackage, objectMapper))
                .orElseThrow(() -> new PackageNotFoundException("Package not generated"));
    }

    private AgentExtractionRequest toAgentRequest(UUID sessionId, List<SessionDocument> documents) {
        List<AgentExtractionRequest.DocumentPayload> payloads = documents.stream()
                .map(document -> new AgentExtractionRequest.DocumentPayload(
                        document.getId().toString(),
                        document.getDocumentType().name(),
                        document.getExtractedText(),
                        document.getFilename(),
                        document.getSourceLabel()))
                .toList();
        return new AgentExtractionRequest(sessionId.toString(), payloads);
    }

    private ArchInputPackageDto parsePackage(String packageJson) {
        try {
            return objectMapper.readValue(packageJson, ArchInputPackageDto.class);
        } catch (JsonProcessingException e) {
            throw new AgentCommunicationException("Failed to parse package metrics from agent response", e);
        }
    }

    private PackageMetrics extractPackageMetrics(ArchInputPackageDto packageDto) {
        try {
            int criticalGaps = countGapsBySeverity(packageDto.gaps(), "critical");
            int highGaps = countGapsBySeverity(packageDto.gaps(), "high");
            int mediumGaps = countGapsBySeverity(packageDto.gaps(), "medium");
            int gapCount = packageDto.gapCount() > 0 ? packageDto.gapCount() : sizeOf(packageDto.gaps());
            int conflictCount = packageDto.conflictCount() > 0
                    ? packageDto.conflictCount()
                    : sizeOf(packageDto.conflicts());
            BigDecimal readinessScore = readinessScoreService.compute(
                    packageDto.totalRequirements(),
                    packageDto.highConfidenceCount(),
                    packageDto.inferredCount(),
                    criticalGaps,
                    highGaps,
                    mediumGaps,
                    conflictCount);

            return new PackageMetrics(
                    packageDto.totalRequirements(),
                    packageDto.highConfidenceCount(),
                    packageDto.inferredCount(),
                    packageDto.duplicateCount(),
                    gapCount,
                    conflictCount,
                    readinessScore);
        } catch (RuntimeException e) {
            throw new AgentCommunicationException("Failed to derive package metrics", e);
        }
    }

    private int countGapsBySeverity(List<GapAreaDto> gaps, String targetSeverity) {
        if (gaps == null || gaps.isEmpty()) {
            return 0;
        }
        return (int) gaps.stream()
                .filter(gap -> targetSeverity.equals(
                        gap.severity() == null ? "" : gap.severity().toLowerCase(Locale.ROOT)))
                .count();
    }

    private int sizeOf(List<?> values) {
        return values == null ? 0 : values.size();
    }

    private record PackageMetrics(
            int totalRequirements,
            int highConfidenceCount,
            int inferredCount,
            int duplicateCount,
            int gapCount,
            int conflictCount,
            BigDecimal readinessScore
    ) {
    }
}
