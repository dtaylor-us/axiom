package com.lens.api.service;

import com.lens.api.domain.model.ArchitectureEvidence;
import com.lens.api.domain.model.EvidenceType;
import com.lens.api.domain.model.ReviewSession;
import com.lens.api.domain.model.ReviewStatus;
import com.lens.api.exception.BadRequestException;
import com.lens.api.exception.ConflictException;
import com.lens.api.exception.ResourceNotFoundException;
import com.lens.api.repository.ArchitectureEvidenceRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class EvidenceIngestionService {

    private static final int MIN_CONTENT_LENGTH = 50;

    private final ArchitectureEvidenceRepository evidenceRepository;
    private final ReviewSessionService reviewSessionService;

    public EvidenceIngestionService(
            ArchitectureEvidenceRepository evidenceRepository,
            ReviewSessionService reviewSessionService) {
        this.evidenceRepository = evidenceRepository;
        this.reviewSessionService = reviewSessionService;
    }

    @Transactional
    public ArchitectureEvidence submitEvidence(
            UUID sessionId,
            String userId,
            String evidenceType,
            String content,
            String sourceLabel) {
        ReviewSession session = reviewSessionService.getSession(sessionId, userId);
        if (session.getStatus() != ReviewStatus.EVIDENCE_COLLECTION
                && session.getStatus() != ReviewStatus.GAP_ELICITATION) {
            throw new ConflictException("Evidence can only be submitted during evidence collection or gap elicitation");
        }

        if (content == null || content.trim().length() < MIN_CONTENT_LENGTH) {
            throw new BadRequestException("Evidence content must be at least 50 characters");
        }

        EvidenceType parsedType;
        try {
            parsedType = EvidenceType.valueOf(evidenceType);
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException("Unsupported evidence type: " + evidenceType);
        }

        ArchitectureEvidence evidence = new ArchitectureEvidence();
        evidence.setId(UUID.randomUUID());
        evidence.setSessionId(sessionId);
        evidence.setEvidenceType(parsedType);
        evidence.setContent(content.trim());
        evidence.setSourceLabel(sourceLabel);
        evidence.setSubmittedAt(LocalDateTime.now());

        ArchitectureEvidence saved = evidenceRepository.save(evidence);

        if (session.getStatus() == ReviewStatus.EVIDENCE_COLLECTION) {
            reviewSessionService.transitionStatus(sessionId, ReviewStatus.GAP_ELICITATION);
        }

        return saved;
    }

    @Transactional(readOnly = true)
    public List<ArchitectureEvidence> listEvidence(UUID sessionId) {
        return evidenceRepository.findBySessionIdOrderBySubmittedAtAsc(sessionId);
    }

    @Transactional
    public void deleteEvidence(UUID sessionId, UUID evidenceId) {
        ArchitectureEvidence evidence = evidenceRepository.findById(evidenceId)
                .orElseThrow(() -> new ResourceNotFoundException("Evidence not found"));
        if (!evidence.getSessionId().equals(sessionId)) {
            throw new ResourceNotFoundException("Evidence not found");
        }
        evidenceRepository.delete(evidence);
    }
}
