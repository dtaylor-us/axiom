package com.specweaver.api.service;

import java.math.BigDecimal;
import java.util.List;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import com.specweaver.api.domain.model.GeneratedPackage;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionDocument;
import com.specweaver.api.dto.ArchInputPackageDto;
import com.specweaver.api.dto.response.DocumentResponse;
import com.specweaver.api.dto.response.PackageResponse;
import com.specweaver.api.dto.response.SessionResponse;
import com.specweaver.api.exception.AgentCommunicationException;

/**
 * Maps persisted SpecWeaver entities to API response records.
 */
final class ResponseMapper {

    private ResponseMapper() {
    }

    static SessionResponse toSessionResponse(Session session, boolean includeDocuments) {
        List<DocumentResponse> documents = includeDocuments
                ? session.getDocuments().stream().map(ResponseMapper::toDocumentResponse).toList()
                : List.of();
        return new SessionResponse(
                session.getId(),
                session.getUserId(),
                session.getTitle(),
                session.getStatus(),
                session.getCreatedAt(),
                session.getUpdatedAt(),
                session.getArchonConversationId(),
                documents);
    }

    static DocumentResponse toDocumentResponse(SessionDocument document) {
        return new DocumentResponse(
                document.getId(),
                document.getDocumentType(),
                document.getFilename(),
                document.getSourceLabel(),
                document.getStorageKey(),
                document.getExtractedText(),
                document.getStatus(),
                document.getErrorMessage(),
                document.getCreatedAt(),
                document.getProcessedAt());
    }

    static PackageResponse toPackageResponse(
            GeneratedPackage generatedPackage,
            ObjectMapper objectMapper) {
        ArchInputPackageDto packageDto = parsePackage(generatedPackage, objectMapper);
        BigDecimal readinessScore = generatedPackage.getReadinessScore() == null
                ? BigDecimal.ZERO
                : generatedPackage.getReadinessScore();
        return new PackageResponse(
                generatedPackage.getId(),
                generatedPackage.getSession().getId(),
                generatedPackage.getCreatedAt(),
                readinessScore,
                PackageResponse.readinessLabel(readinessScore),
                packageDto.systemDescription(),
                emptyIfNull(packageDto.requirements()),
                emptyIfNull(packageDto.gaps()),
                emptyIfNull(packageDto.conflicts()),
                emptyIfNull(packageDto.sourceDocuments()),
                generatedPackage.getTotalRequirements(),
                generatedPackage.getHighConfidenceCount(),
                generatedPackage.getInferredCount(),
                generatedPackage.getDuplicateCount(),
                generatedPackage.getGapCount(),
                generatedPackage.getConflictCount());
    }

    private static ArchInputPackageDto parsePackage(
            GeneratedPackage generatedPackage,
            ObjectMapper objectMapper) {
        try {
            return objectMapper.readValue(generatedPackage.getPackageJson(), ArchInputPackageDto.class);
        } catch (JsonProcessingException e) {
            throw new AgentCommunicationException("Failed to parse generated package JSON", e);
        }
    }

    private static List<?> emptyIfNull(List<?> values) {
        return values == null ? List.of() : values;
    }
}
