package com.specweaver.api.service;

import java.util.UUID;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.specweaver.api.domain.model.GeneratedPackage;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.dto.ArchInputPackageDto;
import com.specweaver.api.exception.AgentCommunicationException;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.repository.GeneratedPackageRepository;

/**
 * Provides package-related operations that do not require external Archon API calls.
 */
@Service
@RequiredArgsConstructor
public class PackageService {

    private final SessionService sessionService;
    private final GeneratedPackageRepository generatedPackageRepository;
    private final ObjectMapper objectMapper;
    private final BriefFormatter briefFormatter;

    /**
     * Returns the persisted requirements brief for UI handoff to the Archon chat input.
     *
     * <p>If the brief is missing for an existing package, this method generates and saves
     * it so subsequent calls are idempotent.</p>
     *
     * @param sessionId session identifier
     * @param userId authenticated user identifier
     * @return requirements brief text
     */
    @Transactional
    public String getBriefText(UUID sessionId, UUID userId) {
        Session session = sessionService.requireOwnedSession(sessionId, userId);
        GeneratedPackage generatedPackage = generatedPackageRepository.findBySessionId(sessionId)
                .orElseThrow(() -> new PackageNotFoundException("Package not generated"));

        if (generatedPackage.getBriefText() != null && !generatedPackage.getBriefText().isBlank()) {
            return generatedPackage.getBriefText();
        }

        ArchInputPackageDto packageDto = parsePackage(generatedPackage);
        String briefText = briefFormatter.format(packageDto, session);
        generatedPackage.setBriefText(briefText);
        generatedPackageRepository.save(generatedPackage);
        return briefText;
    }

    private ArchInputPackageDto parsePackage(GeneratedPackage generatedPackage) {
        try {
            return objectMapper.readValue(generatedPackage.getPackageJson(), ArchInputPackageDto.class);
        } catch (JsonProcessingException e) {
            throw new AgentCommunicationException("Failed to parse generated package JSON", e);
        }
    }
}
